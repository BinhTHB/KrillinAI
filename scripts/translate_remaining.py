#!/usr/bin/env python3
import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

DEEPL_KEY = "e887c262-298b-445e-81a6-3dbd75f5b3ae:fx"
DEEPL_URL = "https://api-free.deepl.com/v2/translate"

def deepl_translate(text, source="ZH", target="VI"):
    data = json.dumps({
        "text": [text],
        "source_lang": source,
        "target_lang": target,
    }).encode("utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                DEEPL_URL,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return result["translations"][0]["text"]
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                return None

def parse_srt(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    entries = {}
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        idx = int(lines[0])
        timing = lines[1]
        text = '\n'.join(lines[2:])
        entries[idx] = {'timing': timing, 'text': text}
    return entries

def main():
    wd = Path("tasks/douyin-new")
    orig_srt = wd / "origin_language_srt.srt"
    target_srt = wd / "target_language_srt.srt"
    
    orig_entries = parse_srt(orig_srt)
    target_entries = parse_srt(target_srt)
    
    print(f"Original entries: {len(orig_entries)}")
    print(f"Target entries: {len(target_entries)}")
    
    out_blocks = []
    translated_count = 0
    
    for idx in sorted(orig_entries.keys()):
        orig_text = orig_entries[idx]['text']
        orig_timing = orig_entries[idx]['timing']
        
        # Check if already translated correctly
        needs_translation = True
        if idx in target_entries:
            curr_text = target_entries[idx]['text']
            if "DeepL Error" not in curr_text and len(curr_text.strip()) > 0:
                # Use existing translation
                out_blocks.append(f"{idx}\n{orig_timing}\n{curr_text}")
                needs_translation = False
        
        if needs_translation:
            print(f"Translating #{idx}: {orig_text[:50]}...")
            vi_text = deepl_translate(orig_text)
            if vi_text:
                print(f"  -> {vi_text[:50]}")
                out_blocks.append(f"{idx}\n{orig_timing}\n{vi_text}")
                translated_count += 1
            else:
                print(f"  -> FAILED. Keeping original Chinese.")
                out_blocks.append(f"{idx}\n{orig_timing}\n{orig_text}")
            time.sleep(0.3)
            
    # Write to target_language_srt.srt
    with open(target_srt, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks))
        
    print(f"\nDone! Translated {translated_count} entries. Saved to {target_srt}")

if __name__ == "__main__":
    main()
