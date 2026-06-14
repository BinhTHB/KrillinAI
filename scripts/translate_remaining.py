#!/usr/bin/env python3
"""Translate remaining Chinese entries in SRT via DeepL API using Header-based Auth."""
import re, json, time, urllib.request, urllib.parse

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
            if attempt < 2:
                time.sleep(2)
            else:
                return f"[DeepL Error: {e}]"

def main():
    srt_path = "tasks/douyin-new/target_language_srt.srt"
    with open(srt_path, encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n\n+', content.strip())
    translated = 0
    total = len(blocks)
    out_blocks = []

    for i, block in enumerate(blocks):
        lines = block.strip().split('\n')
        if len(lines) < 3:
            out_blocks.append(block)
            continue

        idx = lines[0]
        timing = lines[1]
        text = ' '.join(lines[2:])

        # Check if Chinese (CJK characters > 30%)
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if cjk > len(text) * 0.3:
            print(f"[{i+1}/{total}] #{idx}: {text[:50]}...", end=" -> ", flush=True)
            vi_text = deepl_translate(text)
            print(f"{vi_text[:50]}...", flush=True)
            out_blocks.append(f"{idx}\n{timing}\n{vi_text}")
            translated += 1
            time.sleep(0.3)
        else:
            out_blocks.append(block)

    # Write updated SRT
    out_path = "tasks/douyin-new/target_language_srt_full.srt"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks))
    
    print(f"\nDone! {translated}/{total} entries translated. Saved to {out_path}")

if __name__ == "__main__":
    main()
