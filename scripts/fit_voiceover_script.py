#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from srt_utils import SrtCue, load_srt, write_srt
from voiceover_budget import build_budgets
from translate_gemini import load_config

CJK_RE = re.compile(r'[\u3400-\u9fff]')


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\n|```$', '', text, flags=re.MULTILINE).strip()
    return text


def call_fit_api(items, base_url, api_key, model, prompt_template, strict=False):
    url = base_url.rstrip('/') + '/chat/completions'
    instruction = prompt_template
    if strict:
        instruction += '\n\nRewrite stricter: every fitted_text must be noticeably shorter than current_translation and under max_chars.'
    payload_input = {'cues': items}
    prompt = instruction + '\n\nInput JSON:\n' + json.dumps(payload_input, ensure_ascii=False)
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
        'stream': False,
        'response_format': {'type': 'json_object'},
    }
    for attempt in range(4):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code != 200:
                print(f'API error {r.status_code}: {r.text[:400]}')
                time.sleep(3 * (attempt + 1))
                continue
            data = r.json()
            content = strip_fences(data['choices'][0]['message']['content'])
            parsed = json.loads(content)
            cues = parsed.get('cues', [])
            if isinstance(cues, list):
                by_index = {int(c['index']): str(c.get('fitted_text', '')).strip() for c in cues if 'index' in c}
                return by_index
        except Exception as e:
            print(f'fit API attempt {attempt + 1} failed: {e}')
            time.sleep(3 * (attempt + 1))
    return {}


def fit_texts(source_cues, translated_cues, budgets, args):
    base_url, api_key, model = load_config()
    if not api_key:
        raise RuntimeError('Missing LLM API key in config/config.toml')
    prompt_template = Path(args.prompt_file).read_text(encoding='utf-8')
    fitted = []
    report = []
    total = len(translated_cues)
    for start in range(0, total, args.batch_size):
        batch_src = source_cues[start:start + args.batch_size]
        batch_trans = translated_cues[start:start + args.batch_size]
        batch_budget = budgets[start:start + args.batch_size]
        items = []
        for src, trans, budget in zip(batch_src, batch_trans, batch_budget):
            items.append({
                'index': trans.index,
                'source_text': src.text,
                'current_translation': trans.text,
                'duration': round(budget.allowed_duration, 3),
                'max_chars': budget.max_chars,
            })
        print(f'Fitting batch {start // args.batch_size + 1}/{(total + args.batch_size - 1) // args.batch_size}...')
        replacements = call_fit_api(items, base_url, api_key, model, prompt_template)
        for src, trans, budget in zip(batch_src, batch_trans, batch_budget):
            text = replacements.get(trans.index, trans.text).strip() or trans.text
            too_long = len(text) > int(budget.max_chars * args.char_slack)
            if too_long and args.max_rewrite_rounds > 1:
                retry_item = [{
                    'index': trans.index,
                    'source_text': src.text,
                    'current_translation': text,
                    'duration': round(budget.allowed_duration, 3),
                    'max_chars': budget.max_chars,
                }]
                for _ in range(args.max_rewrite_rounds - 1):
                    retry = call_fit_api(retry_item, base_url, api_key, model, prompt_template, strict=True)
                    new_text = retry.get(trans.index, '').strip()
                    if new_text:
                        text = new_text
                    if len(text) <= int(budget.max_chars * args.char_slack):
                        break
            status = 'pass'
            if CJK_RE.search(text):
                status = 'cjk_left'
            elif len(text) > int(budget.max_chars * args.char_slack):
                status = 'too_long'
            fitted.append(SrtCue(trans.index, trans.start, trans.end, text))
            report.append({
                'index': trans.index,
                'source_text': src.text,
                'original_translation': trans.text,
                'fitted_translation': text,
                'cue_duration': round(trans.duration, 3),
                'allowed_duration': round(budget.allowed_duration, 3),
                'max_chars': budget.max_chars,
                'char_count': len(text),
                'status': status,
            })
        time.sleep(args.batch_delay)
    return fitted, report


def main():
    parser = argparse.ArgumentParser(description='Fit Vietnamese voiceover text to cue timing budgets.')
    parser.add_argument('--source-srt', required=True)
    parser.add_argument('--translated-srt', required=True)
    parser.add_argument('--output-srt', required=True)
    parser.add_argument('--prompt-file', default='scripts/voiceover_fit_prompt.txt')
    parser.add_argument('--report', default='')
    parser.add_argument('--batch-size', type=int, default=10)
    parser.add_argument('--batch-delay', type=float, default=1.0)
    parser.add_argument('--max-rewrite-rounds', type=int, default=3)
    parser.add_argument('--pre-roll', type=float, default=0.15)
    parser.add_argument('--post-roll', type=float, default=0.65)
    parser.add_argument('--min-gap-before-next', type=float, default=0.12)
    parser.add_argument('--chars-per-second', type=float, default=13.0)
    parser.add_argument('--char-slack', type=float, default=1.15)
    args = parser.parse_args()

    source = load_srt(args.source_srt)
    translated = load_srt(args.translated_srt)
    if len(source) != len(translated):
        raise RuntimeError(f'SRT cue count mismatch: source={len(source)} translated={len(translated)}')
    budgets = build_budgets(
        translated,
        pre_roll=args.pre_roll,
        post_roll=args.post_roll,
        min_gap_before_next=args.min_gap_before_next,
        chars_per_second=args.chars_per_second,
    )
    fitted, cue_report = fit_texts(source, translated, budgets, args)
    write_srt(fitted, args.output_srt)
    summary = {
        'total_cues': len(cue_report),
        'passed': sum(1 for c in cue_report if c['status'] == 'pass'),
        'too_long': sum(1 for c in cue_report if c['status'] == 'too_long'),
        'cjk_left': sum(1 for c in cue_report if c['status'] == 'cjk_left'),
    }
    report_path = args.report or str(Path(args.output_srt).with_suffix('.report.json'))
    Path(report_path).write_text(json.dumps({'summary': summary, 'cues': cue_report}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': summary['cjk_left'] == 0, 'summary': summary, 'output_srt': args.output_srt, 'report': report_path}, ensure_ascii=False))


if __name__ == '__main__':
    main()
