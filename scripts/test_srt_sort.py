#!/usr/bin/env python3
"""
Test sorting original SRT entries by start_time to reconstruct timeline.
"""
import re
from pathlib import Path

def parse_srt(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    for b in blocks:
        lines = b.strip().split('\n')
        if len(lines) < 3:
            continue
        timing = lines[1]
        text = '\n'.join(lines[2:]).strip()
        def parse_time(t):
            h, m, s = t.replace(',', '.').split(':')
            return int(h)*3600 + int(m)*60 + float(s)
        start, end = timing.split(' --> ')
        entries.append({
            'index': int(lines[0]),
            'start': parse_time(start),
            'end': parse_time(end),
            'text': text,
        })
    return entries

def main():
    workdir = Path("tasks/douyin-new")
    entries = parse_srt(workdir / "origin_language_srt.srt")
    print(f"Total entries: {len(entries)}")
    
    # Sort by start_time
    sorted_entries = sorted(entries, key=lambda x: x['start'])
    
    for e in sorted_entries[:15]:
        print(f"Index {e['index']}: {e['start']:.3f} --> {e['end']:.3f} | {e['text']}")

if __name__ == "__main__":
    main()
