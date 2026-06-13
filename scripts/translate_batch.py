#!/usr/bin/env python3
"""
Translate a limited number of failed entries (default 70) using googletrans.
Updates translation files and creates a full target SRT.
Run multiple times until all entries are translated.
"""
import json, time, re, os, sys
from pathlib import Path

def load_failed(workdir):
    failed = []
    files = ['translation_data_0.json','translation_data_1.json']
    for fname in files:
        p = workdir / fname
        if not p.exists():
            continue
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            origin = item.get('OriginText','') or item.get('origin_part','')
            trans = item.get('TranslatedText','') or item.get('translated_part','')
            if not trans or trans==origin or len(trans.strip())<3:
                failed.append({'origin':origin,'item':item,'source_file':fname})
    return failed

def translate_google(text):
    from googletrans import Translator
    t = Translator()
    try:
        res = t.translate(text, src='zh-cn', dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  Google error:',e)
        return None

def process(failed, limit=70, batch=5, delay=2):
    total = len(failed)
    to_do = failed[:limit]
    processed = 0
    success = 0
    for i in range(0, len(to_do), batch):
        batch_items = to_do[i:i+batch]
        print(f"\nBatch {i//batch+1}: {len(batch_items)} entries")
        for j, entry in enumerate(batch_items,1):
            orig = entry['origin']
            print(f"  [{j}/{len(batch_items)}] {orig[:40]}...")
            tr = translate_google(orig)
            if tr:
                entry['item']['TranslatedText'] = tr
                entry['item']['TranslationSource'] = 'googletrans_fallback'
                entry['item']['TranslationSuccess'] = True
                success+=1
                print(f"    ✓ {tr[:30]}")
            else:
                entry['item']['TranslationSuccess'] = False
                print('    ✗ failed')
            processed+=1
            time.sleep(0.3)
        if i+batch < len(to_do):
            print(f"Waiting {delay}s before next batch...")
            time.sleep(delay)
    print(f"\nProcessed {processed}/{total} failed entries. Success {success}/{processed} ({success/processed*100 if processed else 0:.1f}%)")
    return success

def update_files(workdir, failed):
    # Re‑write updated translation files
    grouped = {'translation_data_0.json':[], 'translation_data_1.json':[]}
    for e in failed:
        grouped[e['source_file']].append(e['item'])
    for fname, items in grouped.items():
        path = workdir / fname
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            original = json.load(f)
        # replace items by matching origin
        lookup = { (it.get('OriginText') or it.get('origin_part')): it for it in items }
        for i, it in enumerate(original):
            key = it.get('OriginText') or it.get('origin_part')
            if key in lookup:
                original[i] = lookup[key]
        out = workdir / f"{fname.split('.')[0]}_updated.json"
        with open(out,'w',encoding='utf-8') as f:
            json.dump(original, f, ensure_ascii=False, indent=2)
        print(f"Saved updated {out}")

def create_full_srt(workdir):
    origin_path = workdir / 'origin_language_srt_fixed.srt'
    with open(origin_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    trans_map = {}
    # Load all translations (updated files)
    for fname in ['translation_data_0_updated.json','translation_data_1_updated.json']:
        p = workdir / fname
        if p.exists():
            with open(p,'r',encoding='utf-8') as f:
                data = json.load(f)
            for it in data:
                o = it.get('OriginText') or it.get('origin_part')
                t = it.get('TranslatedText') or it.get('translated_part')
                if t and t!=o:
                    trans_map[o]=t
    # Build new SRT
    out_blocks=[]
    idx=1
    for block in blocks:
        lines=block.strip().split('\n')
        if len(lines)<3:
            continue
        timestamp=lines[1]
        ori='\n'.join(lines[2:])
        if ori in trans_map:
            out_blocks.append(f"{idx}\n{timestamp}\n{trans_map[ori]}")
            idx+=1
    out_path=workdir/'target_language_srt_full.srt'
    with open(out_path,'w',encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks))
    print(f"Created full SRT: {out_path} ({len(out_blocks)} entries)")

def main():
    workdir=Path('tasks/douyin-test')
    failed=load_failed(workdir)
    if not failed:
        print('No failed translations left.')
        return
    print(f'Found {len(failed)} failed entries.')
    process(failed, limit=70, batch=5, delay=2)
    update_files(workdir, failed)
    create_full_srt(workdir)
    print('\nRun this script again until no failed entries remain.')

if __name__=='__main__':
    main()
