#!/usr/bin/env python3
"""
Translate origin_language_srt.srt to Vietnamese using the official Gemini API
configured in config/config.toml (OpenAI-compatible endpoint).
"""
import sys
import argparse
import re
import time
import json
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gemini_rate_limiter import RequestRateLimiter

def load_config():
    config_path = Path("config/config.toml")
    if not config_path.exists():
        print("ERROR: config/config.toml not found")
        return None, None, None
        
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Simple regex parsing for TOML [llm] section
    llm_section = re.search(r'\[llm\](.*?)(?:\[|$)', content, re.DOTALL)
    if not llm_section:
        print("ERROR: [llm] section not found in config")
        return None, None, None
        
    section_content = llm_section.group(1)
    base_url_match = re.search(r'base_url\s*=\s*"([^"]+)"', section_content)
    api_key_match = re.search(r'api_key\s*=\s*"([^"]+)"', section_content)
    model_match = re.search(r'model\s*=\s*"([^"]+)"', section_content)
    
    base_url = base_url_match.group(1) if base_url_match else None
    api_key = api_key_match.group(1) if api_key_match else None
    model = model_match.group(1) if model_match else None
    
    return base_url, api_key, model

def load_srt_entries(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        entries.append({
            'index': lines[0],
            'timing': lines[1],
            'text': '\n'.join(lines[2:]).strip()
        })
    return entries

def translate_batch(batch, base_url, api_key, model, context_before="", context_after="", asr_ref="", prompt_template="", limiter=None):
    # Target endpoint
    url = base_url.rstrip('/') + '/chat/completions'
    
    if prompt_template:
        prompt = (prompt_template
                  .replace("{asr_ref}", asr_ref)
                  .replace("{before}", context_before)
                  .replace("{sentences_json}", json.dumps([e['text'] for e in batch], ensure_ascii=False))
                  .replace("{after}", context_after))
    else:
        # Fallback default prompt
        prompt = f"""You are a professional Chinese-to-Vietnamese translation expert translating a Chinese Xianxia/Tu Tiên video.
Role relationship: Sư phụ (Master) and Đồ nhi (Disciple).
ASR Reference: {asr_ref}
Context before: {context_before}
OCR Sentences: {json.dumps([e['text'] for e in batch], ensure_ascii=False)}
Context after: {context_after}
Return valid JSON key "translations".
"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
    
    for attempt in range(4):
        try:
            if limiter:
                limiter.wait_and_record()
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                res_data = r.json()
                text_out = res_data['choices'][0]['message']['content'].strip()
                if text_out.startswith("```"):
                    text_out = re.sub(r"^```(?:json)?\n|```$", "", text_out, flags=re.MULTILINE).strip()
                
                data_dict = json.loads(text_out)
                translations = data_dict.get("translations")
                
                if isinstance(translations, list) and len(translations) == len(batch):
                    return translations
                print(f"  Warning: Expected list of length {len(batch)}, got: {translations}")
            else:
                print(f"  API Error {r.status_code}: {r.text}")
            
            time.sleep(3 * (attempt+1))
        except Exception as e:
            print(f"  Error on attempt {attempt+1}: {e}")
            time.sleep(3 * (attempt+1))
    return None

def main():
    parser = argparse.ArgumentParser(description="Translate SRT using Gemini API")
    parser.add_argument("--workdir", type=str, default="tasks/douyin-new", help="Working directory containing origin_language_srt.srt")
    parser.add_argument("--asr-reference", type=str, default="origin_language_srt.asr_backup.srt", help="optional ASR reference SRT used to correct OCR text before translation")
    parser.add_argument("--prompt-file", type=str, default="scripts/translation_prompt.txt", help="prompt template file with {asr_ref}, {before}, {sentences_json}, {after} placeholders")
    parser.add_argument("--rpm-limit", type=int, default=15, help="requests per minute limit for Gemini text API")
    parser.add_argument("--rpd-limit", type=int, default=500, help="requests per day limit for Gemini text API")
    parser.add_argument("--request-log", type=str, default="", help="path to JSON file tracking request timestamps")
    args = parser.parse_args()

    base_url, api_key, model = load_config()
    if not api_key:
        print("ERROR: Failed to retrieve API key from config")
        return
        
    print(f"Using Configured API Endpoint:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    
    workdir = Path(args.workdir)
    origin_srt = workdir / "origin_language_srt.srt"
    output_srt = workdir / "target_language_srt_gemini.srt"
    
    if not origin_srt.exists():
        print(f"ERROR: {origin_srt} does not exist.")
        return
        
    entries = load_srt_entries(origin_srt)
    print(f"Loaded {len(entries)} entries for translation.")

    limiter = RequestRateLimiter(args.rpm_limit, args.rpd_limit, args.request_log or (workdir / 'translate_requests.json'))

    asr_path = workdir / args.asr_reference
    asr_ref = ""
    if asr_path.exists():
        asr_entries = load_srt_entries(asr_path)
        asr_ref = " ".join(e['text'] for e in asr_entries)
        print(f"Loaded ASR reference for OCR correction: {asr_path} entries={len(asr_entries)}")
    else:
        print(f"No ASR reference found at {asr_path}; translating OCR text directly.")
    
    prompt_path = Path(args.prompt_file)
    prompt_template = ""
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding='utf-8')
        print(f"Loaded translation prompt template: {prompt_path}")
    else:
        print(f"No prompt file found at {prompt_path}; using fallback prompt.")
    
    batch_size = 10
    total = len(entries)
    translated_entries = []
    
    for i in range(0, total, batch_size):
        batch = entries[i:i+batch_size]
        batch_idx = i//batch_size + 1
        total_batches = total//batch_size + (1 if total%batch_size != 0 else 0)
        print(f"Translating batch {batch_idx}/{total_batches}...")
        
        before = "\n".join([e['text'] for e in entries[max(0, i-5):i]])
        after = "\n".join([e['text'] for e in entries[i+batch_size:min(total, i+batch_size+5)]])
        
        translations = translate_batch(batch, base_url, api_key, model, before, after, asr_ref, prompt_template, limiter=limiter)
        
        if translations:
            for entry, trans in zip(batch, translations):
                entry['translated'] = trans
                print(f"  {entry['index']}: {entry['text'][:20]} -> {trans[:40]}")
                translated_entries.append(entry)
        else:
            print(f"  Failed to translate batch. Copying original text as fallback.")
            for entry in batch:
                entry['translated'] = entry['text']
                translated_entries.append(entry)
                
        time.sleep(2.0)
        
    with open(output_srt, 'w', encoding='utf-8') as f:
        for e in translated_entries:
            f.write(f"{e['index']}\n")
            f.write(f"{e['timing']}\n")
            f.write(f"{e['translated']}\n\n")
            
    print(f"\nSaved Gemini translations to {output_srt}")
    
    default_target = workdir / "target_language_srt.srt"
    with open(output_srt, 'r', encoding='utf-8') as src:
        with open(default_target, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    print("Updated default target_language_srt.srt with Gemini translations.")

if __name__ == "__main__":
    main()
