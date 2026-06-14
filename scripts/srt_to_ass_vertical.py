#!/usr/bin/env python3
"""
Convert SRT to ASS format optimized for vertical video (720x1280).
Fixes styling issues (fontsize, margin) and subtitle tag syntax.
"""
import re
from pathlib import Path

def srt_to_ass_vertical(srt_path, ass_path):
    """Convert SRT to ASS with vertical styling."""
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    
    # ASS header for horizontal/original video (1280x720)
    ass_content = """[Script Info]
Title: Vertical Vietnamese Subtitle
Original Script: 
ScriptType: v4.00+
PlayDepth: 0
Collisions: Normal
PlayResX: 1280
PlayResY: 720
Timer: 100.0000
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3.0,1.0,2,20,20,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Convert SRT blocks to ASS events
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        index = lines[0]
        timing = lines[1]
        text = '\n'.join(lines[2:])
        
        # Convert timing format: HH:MM:SS,mmm --> H:MM:SS.cc
        def convert_time(t):
            parts = t.replace(',', '.').split(':')
            h = int(parts[0])
            m = int(parts[1])
            s_parts = parts[2].split('.')
            s = int(s_parts[0])
            ms = int(s_parts[1][:2])  # Centiseconds
            return f"{h}:{m:02d}:{s:02d}.{ms:02d}"
        
        start_time, end_time = timing.split(' --> ')
        start_ass = convert_time(start_time)
        end_ass = convert_time(end_time)
        
        # Remove newlines in subtitle text
        text_clean = text.replace('\n', ' ')
        
        # Correct ASS format: {\an2} without duplicate curly braces
        ass_line = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{{\\an2}}{text_clean}\n"
        ass_content += ass_line
    
    # Write ASS file
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    
    print(f"Created ASS file: {ass_path}")
    return ass_path

def main():
    workdir = Path("tasks/douyin-new")
    srt_path = workdir / "target_language_srt_fixed.srt"
    ass_path = workdir / "vertical_vietnamese.ass"
    
    if not srt_path.exists():
        print(f"ERROR: {srt_path} not found")
        return
    
    srt_to_ass_vertical(srt_path, ass_path)
    print("✅ ASS file created for vertical video")

if __name__ == "__main__":
    main()