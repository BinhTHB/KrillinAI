#!/usr/bin/env python3
"""
Fix SRT timing by preserving original start_times and intelligently distributing
entries into groups that share the same start_time.
Algorithm:
  1. Sort entries by start_time (ascending)
  2. Group entries by start_time (rounded to 0.1s tolerance)
  3. Within each group, distribute duration proportional to text length
  4. Each group occupies the window from its start to the next group's start
No more linear redistribution!
"""
import re
from pathlib import Path

workdir = Path("tasks/douyin-new")
origin_srt = workdir / "origin_language_srt.srt"
target_srt = workdir / "target_language_srt.srt"
output_srt = workdir / "target_language_srt_fixed.srt"
video_path = workdir / "origin_video.mp4"

# Get video duration
import subprocess
r = subprocess.run(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"',
                   shell=True, stdout=subprocess.PIPE, text=True)
video_dur = float(r.stdout.strip()) if r.stdout.strip() else 180.3
print(f"Video duration: {video_dur:.3f}s")

# Parse origin SRT for timing info
with open(origin_srt, 'r', encoding='utf-8') as f:
    content = f.read()
blocks = re.split(r'\n\n+', content.strip())

origin_entries = []
for b in blocks:
    lines = b.strip().split('\n')
    if len(lines) < 3:
        continue
    idx = int(lines[0])
    timing = lines[1]
    text = '\n'.join(lines[2:]).strip()
    def parse_time(t):
        h, m, s = t.replace(',', '.').split(':')
        return int(h)*3600 + int(m)*60 + float(s)
    start, end = timing.split(' --> ')
    origin_entries.append({
        'index': idx,
        'start': parse_time(start),
        'end': parse_time(end),
        'text': text,
    })

# Sort by start_time
origin_entries.sort(key=lambda x: (x['start'], x['index']))
print(f"Parsed {len(origin_entries)} entries sorted by start_time")

# Group entries by start_time (rounded to 0.05s tolerance)
groups = []
current_group = [origin_entries[0]]
for e in origin_entries[1:]:
    if abs(e['start'] - current_group[-1]['start']) < 0.1:
        current_group.append(e)
    else:
        groups.append(current_group)
        current_group = [e]
groups.append(current_group)
print(f"Grouped into {len(groups)} groups")

# Parse target language text (Vietnamese) in original SRT index order
with open(target_srt, 'r', encoding='utf-8') as f:
    content = f.read()
blocks = re.split(r'\n\n+', content.strip())
target_text_by_idx = {}
for b in blocks:
    lines = b.strip().split('\n')
    if len(lines) < 3:
        continue
    idx = int(lines[0])
    text = '\n'.join(lines[2:]).strip()
    target_text_by_idx[idx] = text
print(f"Loaded {len(target_text_by_idx)} target texts")

# Assign target text to origin entries (by index)
for e in origin_entries:
    e['target_text'] = target_text_by_idx.get(e['index'], e['text'])

# Build output entries
output_entries = []
gap = 0.15  # minimum gap between entries within a group

for gi, group in enumerate(groups):
    group_start = group[0]['start']
    # End of this group = start of next group (or video_end)
    if gi < len(groups) - 1:
        group_end = groups[gi+1][0]['start']
    else:
        group_end = video_dur
    
    # Ensure minimum group duration
    if group_end - group_start < 0.5:
        group_end = group_start + 0.5
    
    n = len(group)
    if n == 1:
        # Single entry gets the full window
        entry = group[0]
        entry_dur = max(0.5, min(group_end - group_start, 5.0))
        output_entries.append({
            'index': entry['index'],
            'text': entry['target_text'],
            'start': group_start,
            'end': group_start + entry_dur,
        })
    else:
        # Multiple entries: distribute proportionally by target text length
        total_chars = sum(len(e['target_text']) for e in group)
        available = group_end - group_start - (n - 1) * gap
        if available < n * 0.3:
            available = n * 0.3  # force minimum
        
        cursor = group_start
        for i, entry in enumerate(group):
            if total_chars > 0:
                char_ratio = len(entry['target_text']) / total_chars
            else:
                char_ratio = 1.0 / n
            entry_dur = max(0.3, char_ratio * available)
            
            start = cursor
            end = cursor + entry_dur
            if end > group_end - 0.05:
                end = group_end - 0.05
            
            output_entries.append({
                'index': entry['index'],
                'text': entry['target_text'],
                'start': start,
                'end': end,
            })
            cursor = end + gap

# Ensure sequential order (1, 2, 3..., not by start_time)
output_entries.sort(key=lambda x: x['start'])

# Assign sequential indices
for i, e in enumerate(output_entries):
    e['seq'] = i + 1

# Write output SRT
def fmt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

with open(output_srt, 'w', encoding='utf-8') as f:
    for e in output_entries:
        f.write(f"{e['seq']}\n")
        f.write(f"{fmt(e['start'])} --> {fmt(e['end'])}\n")
        f.write(f"{e['text']}\n\n")

total = sum(e['end'] - e['start'] for e in output_entries) + (len(output_entries)-1)*gap
print(f"Saved {len(output_entries)} entries | total timeline: {total:.1f}s")

# Show some entries
print(f"\nFirst 5 entries:")
for e in output_entries[:5]:
    print(f"  {e['seq']}: {fmt(e['start'])} --> {fmt(e['end'])} | {e['text'][:30]}")
print(f"\nLast 5 entries:")
for e in output_entries[-5:]:
    print(f"  {e['seq']}: {fmt(e['start'])} --> {fmt(e['end'])} | {e['text'][:30]}")
