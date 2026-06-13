#!/usr/bin/env python3
"""
Translation script (demo) – processes only first 30 failed entries
using googletrans fallback. This verifies that the library works.
"""
import json, time, re, os, sys
from pathlib import Path

def load_failed(workdir):
    entries = []
    for fname in ['translation_data_0.json','translation_data_1.json']:
        path = Path(workdir)/fname
        if not path.exists():
            continue
        with open(path,encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            origin = item.get('OriginText','') or item.get('origin_part','')
            trans = item.get('TranslatedText','') or item.get('translated_part','')
            if not trans or trans==origin or len(trans.strip())<3:
                entries.append({'origin':origin,'item':item})
    return entries

def translate(text):
    from googletrans import Translator
    t = Translator()
    try:
        res = t.translate(text, src='zh-cn', dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  translate error:',e)
        return None

def main():
    workdir = Path('tasks/douyin-test')
    failed = load_failed(workdir)
    print(f'Loaded {len(failed)} failed entries')
    demo = failed[:30]
    print(f'Processing first {len(demo)} entries')
    for i, e in enumerate(demo,1):
        print(f'[{i}] {e["origin"][:40]}...')
        tr = translate(e['origin'])
        if tr:
            e['item']['TranslatedText'] = tr
            print('  ✓', tr[:30])
        else:
            print('  ✗ failed')
        time.sleep(0.5)
    # Save back to a new file for inspection
    out_path = workdir/'translation_demo.json'
    all_items = []
    for f in ['translation_data_0.json','translation_data_1.json']:
        path = workdir/f
        if path.exists():
            with open(path,encoding='utf-8') as f2:
                all_items.extend(json.load(f2))
    with open(out_path,'w',encoding='utf-8') as f3:
        json.dump(all_items, f3, ensure_ascii=False, indent=2)
    print('Saved demo file:', out_path)

if __name__=='__main__':
    main()
