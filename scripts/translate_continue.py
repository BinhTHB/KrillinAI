#!/usr/bin/env python3
"""
Translate all remaining failed entries.
Reads from *_updated.json first, then falls back to original files.
"""
import json, time, re, sys
from pathlib import Path

def load_all_entries(workdir):
    """Load all entries from updated files first, then originals."""
    all_entries = []
    # Try updated files first
    for base in ['translation_data_0', 'translation_data_1']:
        for suffix in ['_updated.json', '.json']:
            fname = base + suffix
            p = workdir / fname
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        item['_source_file'] = fname
                        all_entries.append(item)
                break  # Found file, no need to try original
    return all_entries

def get_failed_entries(all_entries):
    """Get entries that still need translation."""
    failed = []
    for item in all_entries:
        origin = item.get('OriginText', '') or item.get('origin_part', '')
        trans = item.get('TranslatedText', '') or item.get('translated_part', '')
        if not origin:
            continue
        if not trans or trans == origin or len(trans.strip()) < 3 or trans.startswith('['):
            failed.append({'origin': origin, 'item': item})
    return failed

def translate_google(text):
    from googletrans import Translator
    t = Translator()
    try:
        res = t.translate(text, src='zh-cn', dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  Google error:', e)
        return None

def process_batch(entries, batch_size=5, delay=1):
    """Translate entries in batches."""
    total = len(entries)
    success = 0
    for i in range(0, total, batch_size):
        batch = entries[i:i+batch_size]
        print(f'\nBatch {i//batch_size + 1}: {len(batch)} entries')
        for j, entry in enumerate(batch, 1):
            orig = entry['origin']
            print(f'  [{j}/{len(batch)}] {orig[:40]}...')
            tr = translate_google(orig)
            if tr:
                entry['item']['TranslatedText'] = tr
                entry['item']['TranslationSource'] = 'googletrans_fallback'
                success += 1
                print(f'    ✓ {tr[:30]}...')
            else:
                print('    ✗ failed')
            time.sleep(0.3)
        if i + batch_size < total:
            print(f'Waiting {delay}s...')
            time.sleep(delay)
    print(f'\nTranslated {success}/{total} entries')
    return success

def create_srt(workdir, all_entries):
    """Create target SRT from all translated entries."""
    trans_map = {}
    for item in all_entries:
        origin = item.get('OriginText', '') or item.get('origin_part', '')
        trans = item.get('TranslatedText', '') or item.get('translated_part', '')
        if origin and trans and trans != origin and len(trans.strip()) >= 3:
            trans_map[origin] = trans
    
    origin_path = workdir / 'origin_language_srt_fixed.srt'
    with open(origin_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    out_blocks = []
    idx = 1
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        timestamp = lines[1]
        orig = '\n'.join(lines[2:])
        if orig in trans_map:
            out_blocks.append(f"{idx}\n{timestamp}\n{trans_map[orig]}")
            idx += 1
    
    out_path = workdir / 'target_language_srt_final.srt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks))
    print(f'Created {out_path} with {idx-1} entries')

def main():
    workdir = Path('tasks/douyin-test')
    all_entries = load_all_entries(workdir)
    print(f'Total entries loaded: {len(all_entries)}')
    
    failed = get_failed_entries(all_entries)
    print(f'Entries needing translation: {len(failed)}')
    
    if not failed:
        print('All entries already translated!')
        create_srt(workdir, all_entries)
        return
    
    success = process_batch(failed, batch_size=5, delay=1)
    
    if success > 0:
        create_srt(workdir, all_entries)
        print(f'\nDONE! Run TTS with: tasks/douyin-test/target_language_srt_final.srt')
    else:
        print('\nNo translations succeeded.')

if __name__ == '__main__':
    main()