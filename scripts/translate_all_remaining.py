#!/usr/bin/env python3
"""
Translate all remaining failed entries in one go.
Reads from updated translation files and continues where left off.
"""
import json, time, re, sys, os
from pathlib import Path

def get_all_entries(workdir):
    """Load all entries from updated files (or original if updated not exists)."""
    entries = []
    # Try updated files first
    for base in ['translation_data_0', 'translation_data_1']:
        updated = workdir / f'{base}_updated.json'
        original = workdir / f'{base}.json'
        if updated.exists():
            with open(updated, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif original.exists():
            with open(original, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            continue
        if isinstance(data, list):
            for item in data:
                item['_source_file'] = base + '.json'
                entries.append(item)
    return entries

def translate_google(text):
    from googletrans import Translator
    t = Translator()
    try:
        res = t.translate(text, src='zh-cn', dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  Google error:', e)
        return None

def main():
    workdir = Path('tasks/douyin-test')
    all_entries = get_all_entries(workdir)
    print(f'Total entries: {len(all_entries)}')
    
    # Find entries that still need translation
    need_trans = []
    for idx, item in enumerate(all_entries):
        origin = item.get('OriginText', '') or item.get('origin_part', '')
        trans = item.get('TranslatedText', '') or item.get('translated_part', '')
        if not origin:
            continue
        if (not trans or trans == origin or len(trans.strip()) < 3 or
            trans.startswith('[') or 'origin_part' in trans):
            need_trans.append((idx, item, origin))
    
    if not need_trans:
        print('All entries already translated.')
        # Create final SRT
        create_srt(workdir, all_entries)
        return
    
    print(f'Entries needing translation: {len(need_trans)}')
    
    # Translate in batches of 10 with 2s delay
    success = 0
    batch_size = 10
    delay = 2
    total = len(need_trans)
    
    for i in range(0, total, batch_size):
        batch = need_trans[i:i+batch_size]
        print(f'\nBatch {i//batch_size + 1}: {len(batch)} entries')
        for j, (idx, item, origin) in enumerate(batch, 1):
            print(f'  [{j}/{len(batch)}] {origin[:50]}...')
            trans = translate_google(origin)
            if trans:
                item['TranslatedText'] = trans
                item['TranslationSource'] = 'googletrans_fallback'
                item['TranslationSuccess'] = True
                success += 1
                print(f'    ✓ {trans[:40]}...')
            else:
                item['TranslationSuccess'] = False
                print('    ✗ Failed')
            time.sleep(0.5)  # small delay between calls
        if i + batch_size < total:
            print(f'Waiting {delay}s before next batch...')
            time.sleep(delay)
    
    print(f'\nTranslated {success}/{total} entries successfully.')
    
    # Save updated files
    save_updated_files(workdir, all_entries)
    
    # Create final SRT
    create_srt(workdir, all_entries)

def save_updated_files(workdir, all_entries):
    """Save back to *_updated.json files, grouped by source."""
    groups = {}
    for item in all_entries:
        src = item.pop('_source_file', 'translation_data_0.json')
        if src not in groups:
            groups[src] = []
        groups[src].append(item)
    
    for src, items in groups.items():
        # Keep original filename pattern but as _updated
        base = src.replace('.json', '')
        out_path = workdir / f'{base}_updated.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f'Saved {out_path}')

def create_srt(workdir, all_entries):
    """Create target_language_srt_final.srt from all translated entries."""
    # Build map from origin text to translation
    trans_map = {}
    for item in all_entries:
        origin = item.get('OriginText', '') or item.get('origin_part', '')
        trans = item.get('TranslatedText', '') or item.get('translated_part', '')
        if origin and trans and trans != origin and len(trans.strip()) >= 3:
            trans_map[origin] = trans
    
    # Read origin SRT to get timing
    origin_srt = workdir / 'origin_language_srt_fixed.srt'
    with open(origin_srt, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    
    # Create new SRT with translated text
    out_lines = []
    idx = 1
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        timestamp = lines[1]
        origin_text = '\n'.join(lines[2:])
        trans = trans_map.get(origin_text)
        if trans:
            out_lines.append(str(idx))
            out_lines.append(timestamp)
            out_lines.append(trans)
            out_lines.append('')
            idx += 1
    
    out_path = workdir / 'target_language_srt_final.srt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    
    print(f'\nCreated final SRT: {out_path} with {idx-1} entries')
    print(f'Coverage: {idx-1}/{len(blocks)} ({((idx-1)/len(blocks)*100):.1f}%)')

if __name__ == '__main__':
    main()