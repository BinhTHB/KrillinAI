#!/usr/bin/env python3
import argparse
import asyncio
import json
import re
import subprocess
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
from gemini_rate_limiter import RequestRateLimiter

try:
    from controlled_tts_segment_freezing_dub import gemini_tts_text, load_api_key, get_duration
except ImportError as e:
    print(f"Failed to import from controlled_tts_segment_freezing_dub: {e}")
    sys.exit(1)


def call_fit_api_strict(items, base_url, api_key, model, prompt_template, limiter=None):
    url = base_url.rstrip('/') + '/chat/completions'
    instruction = prompt_template + '\n\nRewrite stricter: each fitted_text must be noticeably shorter and under max_chars.'
    payload_input = {'cues': items}
    prompt = instruction + '\n\nInput JSON:\n' + json.dumps(payload_input, ensure_ascii=False)
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.1,
        'stream': False,
        'response_format': {'type': 'json_object'},
    }
    for attempt in range(4):
        try:
            if limiter:
                limiter.wait_and_record()
            r = requests.post(url, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}, json=payload, timeout=90)
            if r.status_code != 200:
                time.sleep(3 * (attempt + 1))
                continue
            data = r.json()
            content = data['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\n|```$', '', content, flags=re.MULTILINE).strip()
            parsed = json.loads(content)
            cues = parsed.get('cues', [])
            by_index = {int(c['index']): str(c.get('fitted_text', '')).strip() for c in cues if 'index' in c}
            return by_index
        except Exception as e:
            print(f'fit API attempt {attempt + 1} failed: {e}')
            time.sleep(3 * (attempt + 1))
    return {}


async def generate_and_measure(cue, cache_dir, api_key, model, voice, limiter=None):
    wav_path = cache_dir / f"cue_{cue.index:04d}.wav"
    if limiter:
        limiter.wait_and_record()
    ok = await gemini_tts_text(cue.text, wav_path, api_key, model, voice, retries=2)
    if not ok or not wav_path.exists():
        return None, 0.0
    dur = get_duration(wav_path)
    return wav_path, dur


async def validate_tts(
    cues, budgets, cache_dir, api_key, model, voice,
    base_url, fit_model, prompt_template, args, limiter=None
):
    report = []
    over_budget = []
    for i, cue in enumerate(cues):
        budget = budgets[i]
        wav_path, dur = await generate_and_measure(cue, cache_dir, api_key, model, voice, limiter)
        if not wav_path:
            report.append({
                'index': cue.index,
                'text': cue.text,
                'tts_duration': 0.0,
                'allowed_duration': budget.allowed_duration,
                'required_speed': 999.0,
                'status': 'tts_failed',
            })
            continue
        required_speed = dur / budget.allowed_duration if budget.allowed_duration > 0 else 999.0
        status = 'pass'
        if required_speed > args.hard_speed:
            status = 'freeze_fallback'
        elif required_speed > args.max_speed:
            status = 'rewrite_needed'
        elif required_speed > 1.0:
            status = 'speedup_ok'
        report.append({
            'index': cue.index,
            'text': cue.text,
            'tts_duration': round(dur, 3),
            'allowed_duration': round(budget.allowed_duration, 3),
            'required_speed': round(required_speed, 3),
            'status': status,
        })
        if status == 'rewrite_needed':
            over_budget.append((i, cue, budget, dur))
    return report, over_budget


async def main():
    parser = argparse.ArgumentParser(description='Validate TTS duration fits cue budgets, rewrite if needed.')
    parser.add_argument('--srt', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--report', default='')
    parser.add_argument('--provider', default='gemini')
    parser.add_argument('--voice', default='Aoede')
    parser.add_argument('--model', default='gemini-2.5-flash-preview-native-audio-dialog')
    parser.add_argument('--max-speed', type=float, default=1.15)
    parser.add_argument('--hard-speed', type=float, default=1.25)
    parser.add_argument('--pre-roll', type=float, default=0.15)
    parser.add_argument('--post-roll', type=float, default=0.65)
    parser.add_argument('--min-gap-before-next', type=float, default=0.12)
    parser.add_argument('--chars-per-second', type=float, default=13.0)
    parser.add_argument('--max-rewrite-rounds', type=int, default=3)
    parser.add_argument('--prompt-file', default='scripts/voiceover_fit_prompt.txt')
    parser.add_argument('--rpm-limit', type=int, default=15, help='requests per minute limit for Gemini requests')
    parser.add_argument('--rpd-limit', type=int, default=500, help='requests per day limit for Gemini requests')
    parser.add_argument('--request-log', type=str, default='', help='path to JSON file tracking request timestamps')
    args = parser.parse_args()

    cues = load_srt(args.srt)
    budgets = build_budgets(
        cues,
        pre_roll=args.pre_roll,
        post_roll=args.post_roll,
        min_gap_before_next=args.min_gap_before_next,
        chars_per_second=args.chars_per_second,
    )
    cache_dir = Path(args.out_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    api_key = load_api_key()
    if not api_key:
        print('ERROR: No Gemini API key found in config/config.toml')
        return

    base_url, _, fit_model = load_config()
    prompt_template = Path(args.prompt_file).read_text(encoding='utf-8')

    limiter = RequestRateLimiter(args.rpm_limit, args.rpd_limit, args.request_log or (cache_dir / 'requests.json'))

    report, over_budget = await validate_tts(
        cues, budgets, cache_dir, api_key, args.model, args.voice,
        base_url, fit_model, prompt_template, args, limiter=limiter
    )

    for rnd in range(args.max_rewrite_rounds):
        if not over_budget:
            break
        print(f'Rewrite round {rnd + 1}: {len(over_budget)} cues over budget')
        items = []
        for i, cue, budget, dur in over_budget:
            items.append({
                'index': cue.index,
                'source_text': '',
                'current_translation': cue.text,
                'duration': round(budget.allowed_duration, 3),
                'max_chars': budget.max_chars,
            })
        replacements = call_fit_api_strict(items, base_url, api_key, fit_model, prompt_template, limiter=limiter)
        new_over = []
        for i, cue, budget, dur in over_budget:
            new_text = replacements.get(cue.index, '').strip() or cue.text
            cues[i] = SrtCue(cue.index, cue.start, cue.end, new_text)
            wav_path = cache_dir / f"cue_{cue.index:04d}.wav"
            limiter.wait_and_record()
            ok = await gemini_tts_text(new_text, wav_path, api_key, args.model, args.voice, retries=2)
            if not ok:
                report[i]['status'] = 'tts_failed'
                continue
            new_dur = get_duration(wav_path)
            required_speed = new_dur / budget.allowed_duration if budget.allowed_duration > 0 else 999.0
            status = 'pass'
            if required_speed > args.hard_speed:
                status = 'freeze_fallback'
            elif required_speed > args.max_speed:
                status = 'rewrite_needed'
            elif required_speed > 1.0:
                status = 'speedup_ok'
            report[i]['text'] = new_text
            report[i]['tts_duration'] = round(new_dur, 3)
            report[i]['required_speed'] = round(required_speed, 3)
            report[i]['status'] = status
            if status == 'rewrite_needed':
                new_over.append((i, cues[i], budget, new_dur))
        over_budget = new_over

    summary = {
        'total_cues': len(report),
        'passed': sum(1 for r in report if r['status'] == 'pass'),
        'speedup_ok': sum(1 for r in report if r['status'] == 'speedup_ok'),
        'rewrite_needed': sum(1 for r in report if r['status'] == 'rewrite_needed'),
        'freeze_fallback': sum(1 for r in report if r['status'] == 'freeze_fallback'),
        'tts_failed': sum(1 for r in report if r['status'] == 'tts_failed'),
    }
    report_path = args.report or str(cache_dir / 'tts_fit_report.json')
    Path(report_path).write_text(json.dumps({'summary': summary, 'cues': report}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': summary['rewrite_needed'] == 0 and summary['tts_failed'] == 0, 'summary': summary, 'report': report_path}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
