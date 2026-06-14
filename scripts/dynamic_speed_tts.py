#!/usr/bin/env python3
"""
Dynamic Speed Adjustment for TTS segments.
Speeds up individual chunks that have too much text for their duration.
"""
import os
import re
import subprocess
from pathlib import Path

def parse_time(t_str):
    h, m, s = t_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def process_dynamic_speed(workdir):
    workdir = Path(workdir)
    raw_dir = workdir / "dubbing" / "segments" / "raw"
    processed_dir = workdir / "dubbing" / "segments" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Read SRT to match chunks with text length and duration
    with open(workdir / "target_language_srt.srt", 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        idx = int(lines[0])
        timing = lines[1]
        text = ' '.join(lines[2:])
        
        start_str, end_str = timing.split(' --> ')
        duration = parse_time(end_str) - parse_time(start_str)
        char_count = len(text)
        
        # Segment audio file
        input_wav = raw_dir / f"chunk_{idx}.wav"
        output_wav = processed_dir / f"chunk_{idx}.wav"
        
        if not input_wav.exists():
            continue
            
        # Calculate optimal speed
        # Target speed: chars per second
        speed = char_count / duration if duration > 0 else 0
        
        # If speed is too fast, speed up the audio
        if speed > 15:
            # Calculate required speed factor (capped at 1.4x for safety)
            factor = min(1.4, speed / 11.0)
            print(f"Chunk {idx}: speed {speed:.1f} chars/sec. Speed factor: {factor:.2f}x")
            
            # Apply FFmpeg atempo filter
            cmd = [
                'ffmpeg', '-y', '-i', str(input_wav),
                '-filter:a', f'atempo={factor}',
                str(output_wav)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Copy as is
            # (or just use symbolic link/copy)
            import shutil
            shutil.copy(input_wav, output_wav)
            
    print("✅ Processed dynamic speed for all chunks")

if __name__ == "__main__":
    process_dynamic_speed("tasks/douyin-test")