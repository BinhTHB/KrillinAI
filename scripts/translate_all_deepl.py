#!/usr/bin/env python3
"""
Translate ALL SRT entries with DeepL API.
Process in small batches with error handling.
"""
import deepl
import re
import time
import sys
from pathlib import Path

def translate_batch(entries, start_idx=0, batch_size=10):
    """Translate a batch of entries."""
    translator = deepl.Translator('e887c262-298b-445e-81a6-3dbd75f5b3ae:fx')
    translated = []
    failed = 0
    
    for i, entry in enumerate(entries[start_idx:start_idx+batch_size], start_idx+1):
        try:
            result = translator.translate_text(
                entry['text'], 
                source_lang='ZH', 
                target_lang='VI'
            )
            entry['translated'] = result.text
            translated.append(entry)
            print(f"✓ [{i}] {entry['text'][:30]}...")
        except Exception as e:
            print(f"✗ [{i}] Error: {e}")
            entry['translated'] = entry['text']  # Keep original
            translated.append(entry)
            failed += 1
        
        time.sleep(0.5)  # Rate limit
    
    return translated, failed

def main():
    srt_path = Path("tasks/douyin-test/origin_language_srt.srt")
    
    # Load all entries
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    all_entries = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        all_entries.append({
            'index': lines[0],
            'timing': lines[1],
            'text': '\n'.join(lines[2:]),
            'translated': None
        })
    
    print(f"Total entries to translate: {len(all_entries)}")
    
    # Process in batches
    batch_size = 10
    all_translated = []
    total_failed = 0
    
    for batch_num in range(0, len(all_entries), batch_size):
        end_idx = min(batch_num + batch_size, len(all_entries))
        print(f"\n--- Batch {batch_num//batch_size + 1} ({batch_num+1}-{end_idx}) ---")
        
        batch, failed = translate_batch(all_entries, batch_num, batch_size)
        all_translated.extend(batch)
        total_failed += failed
        
        if batch_num + batch_size < len(all_entries):
            print("Waiting 3s before next batch...")
            time.sleep(3)
    
    # Create output SRT
    output_lines = []
    for entry in all_translated:
        output_lines.append(f"{entry['index']}")
        output_lines.append(f"{entry['timing']}")
        output_lines.append(f"{entry['translated']}")
        output_lines.append("")
    
    output_path = Path("tasks/douyin-test/target_language_srt.srt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\n✅ Translation complete!")
    print(f"   Success: {len(all_entries) - total_failed}/{len(all_entries)}")
    print(f"   Failed: {total_failed}")
    print(f"   Output: {output_path}")

if __name__ == "__main__":
    main()