#!/usr/bin/env python3
"""
Compress Vietnamese translations to fit original Chinese timing.
Keep meaning but shorten text to fit normal reading speed (~12 chars/sec).
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
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

def compress_text_vietnamese(text, max_duration):
    """
    Compress text to fit within max_duration at normal reading speed.
    Normal Vietnamese: ~12 chars/sec
    """
    # Simple compression rules
    text = text.strip()
    
    # Calculate max chars for this duration
    max_chars = int(max_duration * 12)  # 12 chars/sec
    
    if len(text) <= max_chars:
        return text
    
    # If text too long, compress it
    # Remove filler words, reduce redundancy
    compress_patterns = [
        (r'thực sự\s*', ''),
        (r'và\s*', ''),
        (r'mà\s*', 'nhưng '),
        (r'như thế nào', 'thế nào'),
        (r'như thế', 'thế'),
        (r'có\s*biết\s*', 'biết '),
        (r'đến\s*mức\s*nào', ''),
        (r'không\s*', 'k? '),
        (r'sau\s+khi\b', 'sau'),
        (r'trước\s+khi\b', 'trước'),
        (r'bắt\s+đầu\s*từ\b', 'từ'),
        (r'hoàn\s*toàn\b', ''),
        (r'thực\s*ra\b', ''),
        (r'nói\s*chung\b', ''),
        (r'nói\s*tóm\s*lại\b', ''),
        (r'và\s*như\s*vậy\b', ''),
    ]
    
    original = text
    for pattern, replacement in compress_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # If still too long, truncate with ellipsis
    if len(text) > max_chars:
        text = text[:max_chars-3].rsplit(' ', 1)[0] + '...'
    
    # Remove double spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text if text else original[:max_chars-3] + '...'

def main():
    workdir = Path("tasks/douyin-test")
    input_srt = workdir / "target_language_srt.srt"
    output_srt = workdir / "target_language_srt_compressed.srt"
    
    with open(input_srt, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    new_blocks = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        index = lines[0]
        timing = lines[1]
        text = '\n'.join(lines[2:])
        
        start_str, end_str = timing.split(' --> ')
        start = parse_time(start_str)
        end = parse_time(end_str)
        duration = end - start
        
        # Compress text
        text_compressed = compress_text_vietnamese(text, duration)
        
        new_blocks.append(f"{index}\n{timing}\n{text_compressed}")
        
        if len(text) > len(text_compressed) + 5:
            print(f"Compressed: {text[:40]}...")
            print(f"  → {text_compressed[:40]}... ({len(text)} → {len(text_compressed)} chars)")
    
    # Write compressed SRT
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_blocks))
    
    print(f"\n✅ Created compressed SRT: {output_srt}")

if __name__ == "__main__":
    main()