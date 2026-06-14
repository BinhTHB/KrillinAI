#!/usr/bin/env python3
"""
Align SRT entries to actual speech segments detected from the video's audio track.
Uses FFmpeg silence detection (silencedetect) to find speech regions.
"""
import re
import json
import math
import subprocess
from pathlib import Path


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"ERROR: {cmd}")
        print(result.stderr[:500])
    return result


def get_dur(path):
    r = run_cmd(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{path}"')
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


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


def detect_speech(audio_path, noise=-45):
    """Detect speech regions by finding non-silence intervals in audio."""
    r = run_cmd(f'ffmpeg -hide_banner -nostats -i "{audio_path}" -af silencedetect=noise={noise}dB:d=0.3 -f null -')
    stderr = r.stderr
    
    silence_starts = []
    silence_ends = []
    for line in stderr.split('\n'):
        if 'silence_start:' in line:
            try:
                val = float(line.split('silence_start:')[1].strip())
                silence_starts.append(val)
            except:
                pass
        elif 'silence_end:' in line:
            try:
                val = float(line.split('silence_end:')[1].strip().split()[0])
                silence_ends.append(val)
            except:
                pass
    
    # Speech = gaps between silence regions
    speech = []
    duration = get_dur(audio_path)
    
    if not silence_starts and not silence_ends:
        return [{'start': 0, 'end': duration}]
    
    cursor = 0.0
    for end, start in zip(silence_ends, silence_starts[1:] if len(silence_starts) > 1 else [duration]):
        if start - end > 0.1:
            speech.append({'start': end, 'end': start})
    
    # If detection failed, fall back to evenly distributed segments
    if not speech:
        duration = get_dur(audio_path)
        return [{'start': 0, 'end': duration}]
    
    return speech


def align_entries_to_speech(entries, speech_segments):
    """Map SRT entries to detected speech segments in order."""
    if len(speech_segments) < len(entries):
        # Stretch speech segments to cover all entries
        extended = speech_segments.copy()
        if extended:
            last_end = extended[-1]['end']
            last_start = extended[-1]['start']
            gap = max(0.15, (last_end - last_start) / max(1, len(extended)-1))
            while len(extended) < len(entries):
                new_start = extended[-1]['end'] + gap
                new_end = new_start + gap
                extended.append({'start': new_start, 'end': new_end})
        speech_segments = extended
    
    aligned = []
    for i, entry in enumerate(entries):
        seg = speech_segments[i] if i < len(speech_segments) else speech_segments[-1]
        aligned.append({
            'index': entry['index'],
            'text': entry['text'],
            'start': seg['start'],
            'end': seg['end'],
        })
    return aligned


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


def write_srt(entries, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, e in enumerate(entries):
            f.write(f"{i+1}\n")
            f.write(f"{format_time(e['start'])} --> {format_time(e['end'])}\n")
            f.write(f"{e['text']}\n\n")


def main():
    workdir = Path("tasks/douyin-new")
    video_path = workdir / "origin_video.mp4"
    input_srt = workdir / "target_language_srt_fixed.srt"
    output_srt = workdir / "target_language_srt_aligned.srt"
    audio_path = workdir / "origin_audio_for_alignment.wav"
    
    # 1. Extract audio for analysis
    print(f"Extracting audio for speech detection...")
    run_cmd(f'ffmpeg -y -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 1 "{audio_path}"')
    
    # 2. Parse SRT
    entries = parse_srt(input_srt)
    print(f"Loaded {len(entries)} entries")
    
    # 3. Detect speech regions
    print(f"Detecting speech regions from audio...")
    speech_segments = detect_speech(audio_path, noise=-45)
    print(f"Detected {len(speech_segments)} speech segments")
    
    # 4. Align entries to speech
    aligned = align_entries_to_speech(entries, speech_segments)
    
    # 5. Write aligned SRT
    write_srt(aligned, output_srt)
    print(f"Saved aligned SRT to {output_srt}")
    
    # 6. Summary
    for i, e in enumerate(aligned[:5]):
        print(f"  {e['index']}: {format_time(e['start'])} --> {format_time(e['end'])} | {e['text'][:30]}")
    print(f"  ...")
    for i, e in enumerate(aligned[-5:], len(aligned)-5):
        print(f"  {e['index']}: {format_time(e['start'])} --> {format_time(e['end'])} | {e['text'][:30]}")

if __name__ == "__main__":
    main()
