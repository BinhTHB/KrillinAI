#!/usr/bin/env python3
"""
Segment-based freezing dubbing with per-segment subtitle burning.
Processes each SRT entry individually.
If the segment start time exceeds original video duration, creates a static video from the video's last frame.
If TTS is longer than original segment, freezes the last frame.
Handles edge-tts network errors with persistent retries.
"""
import re
import os
import time
import shutil
import subprocess
from pathlib import Path

EDGE_TTS_PY = None

def find_edge_tts_python():
    candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "Scripts" / "python.exe",
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
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

def tts_entry(edge_py, text, output_wav, voice="vi-VN-HoaiMyNeural"):
    """Generate TTS for a single entry text with persistent retry logic."""
    txt_file = output_wav.with_suffix(".txt")
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)

    for attempt in range(5):
        if output_wav.exists():
            try:
                output_wav.unlink()
            except:
                pass
        ok = run_cmd(f'"{edge_py}" -m edge_tts --file "{txt_file}" --voice {voice} --write-media "{output_wav}"')
        if ok and output_wav.exists() and get_dur(output_wav) >= 0.05:
            return True
        print(f"  [Attempt {attempt+1}/5] edge_tts failed for: {text[:30]}...retrying...")
        time.sleep(2)
    return False

def write_mini_ass(ass_path, text, duration_sec):
    """Write a tiny ASS file with one subtitle event spanning the whole duration."""
    h = int(duration_sec // 3600)
    m = int((duration_sec % 3600) // 60)
    s = duration_sec % 60
    end_ts = f"{h}:{m:02d}:{s:05.2f}"
    text_clean = text.replace('\n', ' ').replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3.0,1.0,2,20,20,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end_ts},Default,,0,0,0,,{{\\an2}}{text_clean}
"""
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

def main():
    global EDGE_TTS_PY
    EDGE_TTS_PY = find_edge_tts_python()
    if not EDGE_TTS_PY:
        print("ERROR: edge_tts not found. Install with: pip install edge-tts")
        return

    workdir = Path("tasks/douyin-new")
    srt_path = workdir / "target_language_srt_fixed.srt"
    video_path = workdir / "origin_video.mp4"

    video_dur = get_dur(video_path)
    print(f"Original video duration: {video_dur:.3f}s")

    # Parse SRT entries
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
        srt_dur = parse_time(end) - parse_time(start)
        entries.append({'start': parse_time(start), 'end': parse_time(end), 'text': text, 'srt_dur': srt_dur})
    total = len(entries)
    print(f"Loaded {total} entries from {srt_path.name}")

    segments_dir = workdir / "segments_freezing"
    segments_dir.mkdir(parents=True, exist_ok=True)

    # Export last frame once (for segments beyond original video end)
    last_frame_img = segments_dir / "last_frame.jpg"
    if not last_frame_img.exists():
        run_cmd(f'ffmpeg -y -ss {max(0, video_dur - 0.1):.3f} -i "{video_path}" -vframes 1 -q:v 2 "{last_frame_img}"')

    seg_info = []
    failed = 0

    for i, entry in enumerate(entries):
        idx = i + 1
        text = entry['text']
        orig_dur = entry['srt_dur']

        if 'DeepL Error' in text or not text.strip():
            print(f"  SKIP {idx}: invalid text: {text[:50]}")
            failed += 1
            continue

        # --- TTS via edge_tts (with retry) ---
        tts_raw = segments_dir / f"tts_raw_{idx:03d}.wav"
        ok = tts_entry(EDGE_TTS_PY, text, tts_raw)
        if not ok:
            print(f"  SKIP {idx}: TTS failed after retries")
            failed += 1
            continue

        # Speed up TTS at 1.15x
        tts_speed = segments_dir / f"tts_speed_{idx:03d}.wav"
        ok = run_cmd(f'ffmpeg -y -i "{tts_raw}" -filter:a "atempo=1.15" "{tts_speed}"')
        tts_dur = get_dur(tts_speed)
        if not ok or tts_dur < 0.05:
            tts_dur = get_dur(tts_raw) / 1.15
            shutil.copy2(tts_raw, tts_speed)

        gap = 0.15
        target_dur = tts_dur + gap
        out_video = segments_dir / f"out_v_{idx:03d}.mp4"

        # --- Process video segment ---
        beyond_video = entry['start'] >= video_dur - 0.2

        if beyond_video:
            # Beyond video end: static video from last frame
            run_cmd(f'ffmpeg -y -loop 1 -i "{last_frame_img}" -t {target_dur:.3f}'
                    f' -pix_fmt yuv420p -c:v libx264 -preset fast -crf 23 -r 25 "{out_video}"')
            v_dur = target_dur
        else:
            v_seg = segments_dir / f"v_{idx:03d}.mp4"
            to_time = min(entry['end'], video_dur)
            ok = run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {to_time:.3f} -i "{video_path}"'
                         f' -c:v libx264 -preset fast -crf 23 "{v_seg}"')
            if not ok or get_dur(v_seg) < 0.05:
                # Fallback to static
                run_cmd(f'ffmpeg -y -loop 1 -i "{last_frame_img}" -t {target_dur:.3f}'
                        f' -pix_fmt yuv420p -c:v libx264 -preset fast -crf 23 -r 25 "{out_video}"')
                v_dur = target_dur
            else:
                v_dur = get_dur(v_seg)
                if target_dur > v_dur:
                    freeze_dur = target_dur - v_dur
                    run_cmd(f'ffmpeg -y -i "{v_seg}" -vf "tpad=stop_mode=clone:stop_duration={freeze_dur:.3f}"'
                            f' -c:v libx264 -preset fast -crf 23 "{out_video}"')
                else:
                    shutil.copy2(v_seg, out_video)

        # --- Audio: mix background (15%) with TTS (100%) ---
        out_audio = segments_dir / f"out_a_{idx:03d}.wav"
        combined_dur = max(target_dur, v_dur)
        pad_samples = int(combined_dur * 44100)

        if beyond_video:
            # No background audio: just TTS with padding
            run_cmd(f'ffmpeg -y -i "{tts_speed}" -af "apad=whole_len={pad_samples}" -ac 2 -ar 44100 -acodec pcm_s16le "{out_audio}"')
        else:
            a_seg = segments_dir / f"a_{idx:03d}.wav"
            to_time = min(entry['end'], video_dur)
            run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {to_time:.3f} -i "{video_path}"'
                    f' -vn -acodec pcm_s16le -ar 44100 -ac 2 "{a_seg}"')
            a_dur = get_dur(a_seg)
            combined_dur = max(combined_dur, a_dur)
            pad_samples = int(combined_dur * 44100)
            run_cmd(f'ffmpeg -y -i "{a_seg}" -i "{tts_speed}" -filter_complex '
                    f'"[0:a]volume=0.15,apad=whole_len={pad_samples}[bg];'
                    f'[1:a]adelay=0|0,aformat=sample_rates=44100:channel_layouts=mono,apad=whole_len={pad_samples}[voice];'
                    f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
                    f'-ac 2 -ar 44100 "{out_audio}"')

        # --- Combine video + audio ---
        combined = segments_dir / f"comb_{idx:03d}.mp4"
        run_cmd(f'ffmpeg -y -i "{out_video}" -i "{out_audio}"'
                f' -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -shortest "{combined}"')

        # --- Burn subtitle directly into segment ---
        mini_ass = segments_dir / f"sub_{idx:03d}.ass"
        write_mini_ass(mini_ass, text, combined_dur)
        final_seg = segments_dir / f"final_{idx:03d}.mp4"
        run_cmd(f'ffmpeg -y -i "{combined}" -vf "ass={mini_ass.as_posix()}"'
                f' -c:v libx264 -preset fast -crf 23 -c:a copy "{final_seg}"')

        if not final_seg.exists() or get_dur(final_seg) < 0.05:
            print(f"  SKIP {idx}: final segment creation failed")
            failed += 1
            continue

        seg_info.append(final_seg)
        comb_dur = get_dur(final_seg)
        if idx % 10 == 0 or idx == total:
            print(f"  [{idx}/{total}] srt={orig_dur:.1f}s tts={tts_dur:.1f}s final={comb_dur:.1f}s", flush=True)

    if not seg_info:
        print("ERROR: No segments were successfully processed!")
        return

    print(f"\nProcessed {len(seg_info)}/{total} segments ({failed} failed)", flush=True)

    # Concatenate all segments
    print("Concatenating all segments...", flush=True)
    concat_file = segments_dir / "concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for seg_path in seg_info:
            f.write(f"file '{seg_path.resolve().as_posix()}'\n")

    final_output = workdir / "video_sub_and_tts_fixed.mp4"
    ok = run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}"'
                 f' -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{final_output}"')
    if not ok or not final_output.exists():
        print("ERROR: Final video concat failed!")
        return

    final_dur = get_dur(final_output)
    kb = os.path.getsize(final_output) // 1024 if final_output.exists() else 0
    print(f"\nDone! Final video: {final_output} ({final_dur:.1f}s, {kb}KB)")

if __name__ == "__main__":
    main()
