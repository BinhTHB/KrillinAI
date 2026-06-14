#!/usr/bin/env python3
"""
Stretch SRT timing for Vietnamese translations to allow normal TTS reading speed.
Prevents overlapping by shifting subsequent timestamps.
"""
import re
from pathlib import Path

def parse_time(t_str):
    h, m, s = t_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

def stretch_srt_timing(input_path, output_path, speed_factor=11.0):
    """
    Stretch subtitle timing based on Vietnamese text length.
    Normal speed: ~10-12 characters per second.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        idx = lines[0]
        timing = lines[1]
        text = '\n'.join(lines[2:])
        
        start_str, end_str = timing.split(' --> ')
        start = parse_time(start_str)
        end = parse_time(end_str)
        
        entries.append({
            'index': idx,
            'start': start,
            'end': end,
            'text': text
        })
        
    # Stretch timing
    stretched_entries = []
    current_time = 0.0
    
    for i, entry in enumerate(entries):
        text_len = len(entry['text'].replace('\n', ' '))
        # Calculate minimum duration required for this text
        min_duration = max(1.2, text_len / speed_factor)
        
        # Calculate original gap to previous entry
        orig_start = entry['start']
        orig_duration = entry['end'] - entry['start']
        
        # New start time: maintain at least a small gap or start from current_time
        new_start = max(orig_start, current_time)
        
        # New duration: stretch if original is too short for Vietnamese
        new_duration = max(orig_duration, min_duration)
        new_end = new_start + new_duration
        
        stretched_entries.append({
            'index': entry['index'],
            'start': new_start,
            'end': new_end,
            'text': entry['text']
        })
        
        current_time = new_end + 0.1 # 100ms gap between subtitles
        
    # Write new SRT
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in stretched_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{format_time(entry['start'])} --> {format_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")
            
    print(f"Stretched SRT saved to: {output_path}")
    print(f"Original duration end: {entries[-1]['end']:.2f}s")
    print(f"Stretched duration end: {stretched_entries[-1]['end']:.2f}s")

if __name__ == "__main__":
    workdir = Path("tasks/douyin-test")
    stretch_srt_timing(
        workdir / "target_language_srt.srt", 
        workdir / "target_language_srt_stretched.srt",
        speed_factor=11.0 # 11 chars/sec
    )