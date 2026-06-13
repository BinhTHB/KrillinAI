#!/usr/bin/env python3
"""
Translate up to 30 failed entries using googletrans.
Updates translation files and creates/updates full target SRT.
Run repeatedly until all entries are translated.
"""
import json, time, re, os, sys
from pathlib import Path

def load_failed(workdir):
    failed=[]
    for fname in ['translation_data_0.json','translation_data_1.json']:
        p=workdir/fname
        if not p.exists():
            continue
        with open(p,encoding='utf-8') as f:
            data=json.load(f)
        for it in data:
            origin=it.get('OriginText','') or it.get('origin_part','')
            trans=it.get('TranslatedText','') or it.get('translated_part','')
            if not trans or trans==origin or len(trans.strip())<3:
                failed.append({'origin':origin,'item':it,'source_file':fname})
    return failed

def translate_google(text):
    from googletrans import Translator
    t=Translator()
    try:
        res=t.translate(text,src='zh-cn',dest='vi')
        return res.text if res and res.text else None
    except Exception as e:
        print('  Google error:',e)
        return None

def process(failed, limit=30, batch=5, delay=1):
    to_do=failed[:limit]
    total=len(failed)
    success=0
    for i in range(0,len(to_do),batch):
        batch_items=to_do[i:i+batch]
        print(f"\nBatch {i//batch+1}: {len(batch_items)} entries")
        for j,entry in enumerate(batch_items,1):
            orig=entry['origin']
            print(f"  [{j}/{len(batch_items)}] {orig[:40]}...")
            tr=translate_google(orig)
            if tr:
                entry['item']['TranslatedText']=tr
                entry['item']['TranslationSource']='googletrans_fallback'
                entry['item']['TranslationSuccess']=True
                success+=1
                print(f"    ✓ {tr[:30]}")
            else:
                entry['item']['TranslationSuccess']=False
                print('    ✗ failed')
            time.sleep(0.2)
        if i+batch < len(to_do):
            print(f"Waiting {delay}s before next batch...")
            time.sleep(delay)
    print(f"\nProcessed {len(to_do)}/{total} failed entries. Success {success}/{len(to_do)} ({success/len(to_do)*100 if len(to_do) else 0:.1f}%)")
    return success

def update_files(workdir, failed):
    groups={'translation_data_0.json':[],'translation_data_1.json':[]}
    for e in failed:
        groups[e['source_file']].append(e['item'])
    for fname,items in groups.items():
        p=workdir/fname
        if not p.exists():
            continue
        with open(p,'r',encoding='utf-8') as f:
            original=json.load(f)
        lookup={(it.get('OriginText') or it.get('origin_part')):it for it in items}
        for i,orig_it in enumerate(original):
            key=orig_it.get('OriginText') or orig_it.get('origin_part')
            if key in lookup:
                original[i]=lookup[key]
        out_path=workdir/f"{fname.split('.')[0]}_updated.json"
        with open(out_path,'w',encoding='utf-8') as f:
            json.dump(original,f,ensure_ascii=False,indent=2)
        print(f"Saved {out_path}")

def create_full_srt(workdir):
    # load all translations from updated files (or original if not updated)
    trans_map={}
    for fname in ['translation_data_0_updated.json','translation_data_1_updated.json','translation_data_0.json','translation_data_1.json']:
        p=workdir/fname
        if not p.exists():
            continue
        with open(p,'r',encoding='utf-8') as f:
            data=json.load(f)
        for it in data:
            o=it.get('OriginText') or it.get('origin_part')
            t=it.get('TranslatedText') or it.get('translated_part')
            if t and t!=o:
                trans_map[o]=t
    # read origin SRT
    origin_path=workdir/'origin_language_srt_fixed.srt'
    with open(origin_path,'r',encoding='utf-8') as f:
        content=f.read()
    blocks=re.split(r'\n\n+',content.strip())
    out_blocks=[]
    idx=1
    for block in blocks:
        lines=block.strip().split('\n')
        if len(lines)<3:
            continue
        timestamp=lines[1]
        orig='\n'.join(lines[2:])
        if orig in trans_map:
            out_blocks.append(f"{idx}\n{timestamp}\n{trans_map[orig]}")
            idx+=1
    out_path=workdir/'target_language_srt_full.srt'
    with open(out_path,'w',encoding='utf-8') as f:
        f.write('\n\n'.join(out_blocks))
    print(f"Created full SRT: {out_path} ({len(out_blocks)} entries)")

def main():
    workdir=Path('tasks/douyin-test')
    failed=load_failed(workdir)
    if not failed:
        print('All entries translated already.')
        return
    print(f'Found {len(failed)} failed entries.')
    process(failed,limit=30,batch=5,delay=1)
    update_files(workdir,failed)
    create_full_srt(workdir)
    print('Run again until no failures remain.')

if __name__=='__main__':
    main()
