#!/usr/bin/env python3
"""
Full translation script using googletrans fallback for all failed entries.
Will update translation_data files and generate a complete target SRT.
"""
import json, time, re, os
from pathlib import Path

def load_failed_entries(workdir):
    failed = []
    source_files = ['translation_data_0.json', 'translation_data_1.json']
    for fname in source_files:
        path = workdir / fname
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                origin = item.get('OriginText', '') or item.get('origin_part', '')
                trans = item.get('TranslatedText', '') or item.get('translated_part', '')
                if not trans or trans == origin or len(trans.strip()) < 3:
                    failed.append({'origin': origin, 'item': item, 'source_file': fname})
    return failed

def translate_google(text):
    from googletrans import Translator
    t = Translator()
    try:
        res = t.translate(text, src='zh-cn', dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  Google translate error:', e)
        return None

def batch_translate(failed_entries, batch_size=5, delay=2):
    total = len(failed_entries)
    print(f"Total failed entries to translate: {total}")
    success = 0
    for i in range(0, total, batch_size):
        batch = failed_entries[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} entries)")
        for idx, entry in enumerate(batch, 1):
            origin = entry['origin']
            print(f"  [{idx}/{len(batch)}] {origin[:50]}...")
            trans = translate_google(origin)
            if trans:
                entry['item']['TranslatedText'] = trans
                entry['item']['TranslationSource'] = 'googletrans_fallback'
                entry['item']['TranslationSuccess'] = True
                success += 1
                print(f"    ✓ {trans[:40]}...")
            else:
                entry['item']['TranslationSuccess'] = False
                print("    ✗ Failed")
            time.sleep(0.5)  # slight pause between calls
        if i + batch_size < total:
            print(f"Waiting {delay}s before next batch...")
            time.sleep(delay)
    print(f"\nTranslation finished. Success: {success}/{total} ({success/total*100:.1f}%)")
    return success

def update_translation_files(workdir, failed_entries):
    # Re‑write the two original translation files with updated items
    data_by_file = {'translation_data_0.json': [], 'translation_data_1.json': []}
    for entry in failed_entries:
        data_by_file[entry['source_file']].append(entry['item'])
    
    for fname, items in data_by_file.items():
        path = workdir / fname
        if not path.exists():
            continue
        # Load original full data to preserve entries that were already correct
        with open(path, 'r', encoding='utf-8') as f:
            original = json.load(f)
        # Build a lookup of origin->item for quick merge
        lookup = { (it.get('OriginText') or it.get('origin_part')): it for it in items }
        # Merge back into original list preserving order
        for i, it in enumerate(original):
            key = it.get('OriginText') or it.get('origin_part')
            if key in lookup:
                original[i] = lookup[key]
        # Write updated file
        out_path = workdir / f"{fname.split('.')[0]}_updated.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(original, f, ensure_ascii=False, indent=2)
        print(f"Saved updated file: {out_path}")

def create_target_srt(workdir, translations_map, output_name='target_language_srt_full.srt'):
    # Load origin SRT (fixed version)
    origin_srt_path = workdir / 'origin_language_srt_fixed.srt'
    with open(origin_srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    new_blocks = []
    idx = 1
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        timestamp = lines[1]
        orig_text = '\n'.join(lines[2:])
        trans = translations_map.get(orig_text)
        if trans:
            new_block = f"{idx}\n{timestamp}\n{trans}"
            new_blocks.append(new_block)
            idx += 1
    output_path = workdir / output_name
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_blocks))
    print(f"Created full target SRT: {output_path} ({len(new_blocks)} entries)")

def main():
    workdir = Path('tasks/douyin-test')
    failed = load_failed_entries(workdir)
    if not failed:
        print('No failed entries to translate.')
        return
    # Translate all failed entries
    success = batch_translate(failed, batch_size=5, delay=3)
    # Update translation files with new translations
    update_translation_files(workdir, failed)
    # Build map for SRT creation
    trans_map = { e['origin']: e['item'].get('TranslatedText') for e in failed if e['item'].get('TranslationSuccess') }
    # Create full target SRT
    create_target_srt(workdir, trans_map)
    print('\nAll done. You can now run TTS and render with the new SRT.')

if __name__ == '__main__':
    main()
