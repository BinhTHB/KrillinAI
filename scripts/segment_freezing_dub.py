#!/usr/bin/env python3
"""
Segment-based freezing dubbing: process each subtitle entry individually,
freeze the last frame of each video segment if TTS is longer than the original segment.
Uses python -m edge_tts via Hermes venv for TTS generation.
"""
import re
import os
import shutil
import subprocess
from pathlib import Path

EDGE_TTS_PY = None

def find_edge_tts_python():
    """Find the Hermes venv python that has edge_tts installed."""
    candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "Scripts" / "python.exe",
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3",
        # Herd that's also used by KrillinAI
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # Fallback: try python -m edge_tts
    r = subprocess.run("python -m edge_tts --help", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode == 0:
        return "python"
    return None

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        stderr_short = result.stderr.strip()[:300] if result.stderr else ""
        if stderr_short and "No such file" not in stderr_short:
            print(f"  WARN: {result.returncode} | {stderr_short}")
        return False
    return True

def get_dur(path):
    r = subprocess.run(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{path}"',
                       shell=True, stdout=subprocess.PIPE, text=True)
    try:
        val = r.stdout.strip()
        return float(val) if val else 0.0
    except:
        return 0.0

def main():
    global EDGE_TTS_PY
    EDGE_TTS_PY = find_edge_tts_python()
    if not EDGE_TTS_PY:
        print("ERROR: edge_tts not found. Install with: pip install edge-tts")
        return

    workdir = Path("tasks/douyin-new")
    srt_path = workdir / "target_language_srt.srt"
    video_path = workdir / "origin_video.mp4"
    ass_path = workdir / "vertical_vietnamese.ass"

    # 1. Parse SRT entries  
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
        entries.append({'start': parse_time(start), 'end': parse_time(end), 'text': text})
    print(f"Loaded {len(entries)} entries from SRT")

    # 2. Generate per-entry TTS chunks using edge_tts
    print("Generating per-entry TTS with edge-tts via python -m edge_tts...")
    segments_dir = workdir / "segments_freezing"
    segments_dir.mkdir(parents=True, exist_ok=True)
    
    total_segments = len(entries)
    seg_info = []
    failed = 0
    
    for i, entry in enumerate(entries):
        idx = i + 1
        orig_dur = entry['end'] - entry['start']
        
        # --- Video segment ---
        v_seg = segments_dir / f"v_{idx:03d}.mp4"
        ok = run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {entry["end"]} -i "{video_path}" -c:v libx264 -preset fast -crf 23 "{v_seg}"')
        if not ok:
            print(f"  SKIP {idx}: video segment extraction failed")
            failed += 1
            continue
        v_dur = get_dur(v_seg)
        if v_dur < 0.1:
            failed += 1
            continue
        
        # --- TTS per entry via python -m edge_tts ---
        txt_file = segments_dir / f"text_{idx:03d}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(entry['text'])
        tts_raw = segments_dir / f"tts_raw_{idx:03d}.wav"
        
        ok = run_cmd(f'"{EDGE_TTS_PY}" -m edge_tts --file "{txt_file}" --voice vi-VN-HoaiMyNeural --write-media "{tts_raw}"')
        if not ok or get_dur(tts_raw) < 0.1:
            print(f"  SKIP {idx}: TTS generation failed")
            failed += 1
            continue
        
        # Speed up TTS: atempo=1.15
        tts_speed = segments_dir / f"tts_speed_{idx:03d}.wav"
        ok = run_cmd(f'ffmpeg -y -i "{tts_raw}" -filter:a "atempo=1.15" "{tts_speed}"')
        tts_dur = get_dur(tts_speed)
        if not ok or tts_dur < 0.05:
            tts_dur = get_dur(tts_raw) / 1.15  # estimate
            shutil.copy2(tts_raw, tts_speed)
        
        # Gap between sentences
        gap = 0.15
        target_dur = tts_dur + gap
        
        # --- Process segment ---
        out_video = segments_dir / f"out_v_{idx:03d}.mp4"
        out_audio = segments_dir / f"out_a_{idx:03d}.wav"
        
        if target_dur > v_dur:
            freeze_dur = target_dur - v_dur
            run_cmd(f'ffmpeg -y -i "{v_seg}" -vf "tpad=stop_mode=clone:stop_duration={freeze_dur:.3f}" -c:v libx264 -preset fast -crf 23 "{out_video}"')
        else:
            shutil.copy2(v_seg, out_video)
        
        # --- Audio mixing: original bg (15%) + TTS (100%) ---
        a_seg = segments_dir / f"a_{idx:03d}.wav"
        run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {entry["end"]} -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{a_seg}"')
        a_dur = get_dur(a_seg)
        
        combined_dur = max(target_dur, v_dur, a_dur)
        pad_samples = int(combined_dur * 44100)
        run_cmd(f'ffmpeg -y -i "{a_seg}" -i "{tts_speed}" -filter_complex '
                f'"[0:a]volume=0.15,apad=whole_len={pad_samples}[bg];'
                f'[1:a]adelay=0|0,apad=whole_len={pad_samples}[voice];'
                f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
                f'"{out_audio}"')
        
        combined = segments_dir / f"comb_{idx:03d}.mp4"
        run_cmd(f'ffmpeg -y -i "{out_video}" -i "{out_audio}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -shortest "{combined}"')
        comb_dur = get_dur(combined)
        
        seg_info.append(combined)
        
        if idx % 10 == 0 or idx == total_segments:
            print(f"  [{idx}/{total_segments}] orig={v_dur:.1f}s tts={tts_dur:.1f}s x1.15 final={comb_dur:.1f}s", flush=True)

    if not seg_info:
        print("ERROR: No segments were successfully processed!")
        return
    
    print(f"\nProcessed {len(seg_info)}/{total_segments} segments ({failed} failed)", flush=True)
    
    # 3. Concatenate all segments
    print("Concatenating all segments...", flush=True)
    concat_file = segments_dir / "concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for seg_path in seg_info:
            f.write(f"file '{seg_path.as_posix()}'\n")
    
    final_output = workdir / "transferred_vertical_video_final_fixed.mp4"
    run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{final_output}"')
    
    final_dur = get_dur(final_output)
    kb = os.path.getsize(final_output) // 1024 if final_output.exists() else 0
    print(f"\nDone! Final video: {final_output} ({final_dur:.1f}s, {kb}KB)", flush=True)

if __name__ == "__main__":
    main()
