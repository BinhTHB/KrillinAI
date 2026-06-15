#!/usr/bin/env python3
"""
Segment-based freezing dubbing with dynamic timeline alignment.
Generates TTS directly via Python edge-tts client (async) for speed and stability.
Tuning:
  1. Computes target segment duration based on TTS length (including 1.15x speedup and 0.15s gap).
  2. Dynamically tracks actual start and end times of each segment in the final video.
  3. Generates a new ASS file with exact synchronized timings matching the final video layout.
  4. Encodes the final concatenated video and embeds the aligned ASS subtitles.
"""
import re
import os
import sys
import asyncio
import shutil
import subprocess
from pathlib import Path

# Try importing edge-tts directly
try:
    import edge_tts
except ImportError:
    print("Please install edge-tts: pip install edge-tts")
    sys.exit(1)

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

async def tts_entry_async(text, output_wav, voice="vi-VN-HoaiMyNeural"):
    """Generate TTS using direct edge-tts async API with retry."""
    for attempt in range(5):
        if output_wav.exists():
            try:
                output_wav.unlink()
            except:
                pass
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_wav)
            if output_wav.exists() and get_dur(output_wav) >= 0.05:
                return True
        except Exception as e:
            print(f"  [Attempt {attempt+1}/5] edge-tts error: {e}. Retrying...")
            await asyncio.sleep(2)
    return False

def generate_aligned_ass(ass_path, entries_with_actual_times):
    """Write an ASS file with exact layout (1280x720) and aligned timestamps."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3.0,1.0,2,20,20,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def to_ass_time(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = [header]
    for item in entries_with_actual_times:
        start_ts = to_ass_time(item['actual_start'])
        end_ts = to_ass_time(item['actual_end'])
        text_clean = item['text'].replace('\n', ' ').replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
        lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{{\\an2}}{text_clean}")

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

async def main_async():
    workdir = Path("tasks/douyin-new")
    srt_path = workdir / "target_language_srt_fixed.srt"
    video_path = workdir / "origin_video.mp4"

    if not srt_path.exists():
        print(f"ERROR: {srt_path} not found.")
        return

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
        start_sec = parse_time(start)
        end_sec = parse_time(end)
        entries.append({
            'start': start_sec,
            'end': end_sec,
            'text': text,
            'srt_dur': end_sec - start_sec
        })
        
    total = len(entries)
    print(f"Loaded {total} entries from {srt_path.name}")

    segments_dir = workdir / "segments_freezing"
    if segments_dir.exists():
        shutil.rmtree(segments_dir)
    segments_dir.mkdir(parents=True, exist_ok=True)

    # Export last frame once
    last_frame_img = segments_dir / "last_frame.jpg"
    run_cmd(f'ffmpeg -y -ss {max(0, video_dur - 0.1):.3f} -i "{video_path}" -vframes 1 -q:v 2 "{last_frame_img}"')

    seg_info = []
    failed = 0
    current_timeline = 0.0  # Accumulates time for final alignment

    for i, entry in enumerate(entries):
        idx = i + 1
        text = entry['text']
        orig_dur = entry['srt_dur']

        if not text.strip():
            print(f"  SKIP {idx}: empty text")
            failed += 1
            continue

        # --- 1. TTS Generation ---
        tts_raw = segments_dir / f"tts_raw_{idx:03d}.wav"
        ok = await tts_entry_async(text, tts_raw)
        if not ok:
            print(f"  SKIP {idx}: TTS failed after 5 attempts")
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
        
        # Determine actual duration of this segment
        segment_dur = max(orig_dur, target_dur)
        out_video = segments_dir / f"out_v_{idx:03d}.mp4"

        # --- 2. Process Video Segment ---
        beyond_video = entry['start'] >= video_dur - 0.2

        if beyond_video:
            # Beyond video end: generate static segment from last frame
            run_cmd(f'ffmpeg -y -loop 1 -i "{last_frame_img}" -t {segment_dur:.3f}'
                    f' -pix_fmt yuv420p -c:v libx264 -preset fast -crf 23 -r 25 "{out_video}"')
        else:
            v_seg = segments_dir / f"v_{idx:03d}.mp4"
            to_time = min(entry['end'], video_dur)
            ok = run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {to_time:.3f} -i "{video_path}"'
                         f' -c:v libx264 -preset fast -crf 23 "{v_seg}"')
            if not ok or get_dur(v_seg) < 0.05:
                # Fallback to static
                run_cmd(f'ffmpeg -y -loop 1 -i "{last_frame_img}" -t {segment_dur:.3f}'
                        f' -pix_fmt yuv420p -c:v libx264 -preset fast -crf 23 -r 25 "{out_video}"')
            else:
                v_dur = get_dur(v_seg)
                if segment_dur > v_dur:
                    freeze_dur = segment_dur - v_dur
                    run_cmd(f'ffmpeg -y -i "{v_seg}" -vf "tpad=stop_mode=clone:stop_duration={freeze_dur:.3f}"'
                            f' -c:v libx264 -preset fast -crf 23 "{out_video}"')
                else:
                    shutil.copy2(v_seg, out_video)

        # --- 3. Process Audio Segment ---
        out_audio = segments_dir / f"out_a_{idx:03d}.wav"
        pad_samples = int(segment_dur * 44100)

        if beyond_video:
            # Just TTS padded to target segment duration
            run_cmd(f'ffmpeg -y -i "{tts_speed}" -af "apad=whole_len={pad_samples}" -ac 2 -ar 44100 -acodec pcm_s16le "{out_audio}"')
        else:
            a_seg = segments_dir / f"a_{idx:03d}.wav"
            to_time = min(entry['end'], video_dur)
            run_cmd(f'ffmpeg -y -ss {entry["start"]} -to {to_time:.3f} -i "{video_path}"'
                    f' -vn -acodec pcm_s16le -ar 44100 -ac 2 "{a_seg}"')
            
            run_cmd(f'ffmpeg -y -i "{a_seg}" -i "{tts_speed}" -filter_complex '
                    f'"[0:a]volume=0.15,apad=whole_len={pad_samples}[bg];'
                    f'[1:a]adelay=0|0,aformat=sample_rates=44100:channel_layouts=mono,apad=whole_len={pad_samples}[voice];'
                    f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
                    f'-ac 2 -ar 44100 "{out_audio}"')

        # --- 4. Combine Video + Audio ---
        combined = segments_dir / f"comb_{idx:03d}.mp4"
        run_cmd(f'ffmpeg -y -i "{out_video}" -i "{out_audio}"'
                f' -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -shortest "{combined}"')

        if not combined.exists() or get_dur(combined) < 0.05:
            print(f"  SKIP {idx}: combination failed")
            failed += 1
            continue

        # Log actual alignment mapping
        comb_dur = get_dur(combined)
        entry['actual_start'] = current_timeline
        entry['actual_end'] = current_timeline + comb_dur
        current_timeline += comb_dur

        seg_info.append(combined)
        if idx % 10 == 0 or idx == total:
            print(f"  [{idx}/{total}] srt={orig_dur:.1f}s tts={tts_dur:.1f}s segment={comb_dur:.1f}s timeline={current_timeline:.1f}s", flush=True)

    if not seg_info:
        print("ERROR: No segments were successfully processed!")
        return

    print(f"\nProcessed {len(seg_info)}/{total} segments ({failed} failed)", flush=True)

    # Concatenate all video segments without subtitles burned in first
    print("Concatenating all segments...", flush=True)
    concat_file = segments_dir / "concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for seg_path in seg_info:
            f.write(f"file '{seg_path.resolve().as_posix()}'\n")

    concatenated_raw = segments_dir / "concat_raw.mp4"
    ok = run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}"'
                 f' -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{concatenated_raw}"')
    if not ok or not concatenated_raw.exists():
        print("ERROR: Final video concat failed!")
        return

    # Generate the dynamically aligned ASS file
    aligned_ass_path = workdir / "aligned_vietnamese.ass"
    valid_entries = [e for e in entries if 'actual_start' in e]
    generate_aligned_ass(aligned_ass_path, valid_entries)
    print(f"Generated aligned ASS: {aligned_ass_path}")

    # Burn aligned subtitles into the concatenated video
    final_output = workdir / "video_sub_and_tts_fixed.mp4"
    print("Burning aligned subtitles into final video...", flush=True)
    ok = run_cmd(f'ffmpeg -y -i "{concatenated_raw}" -vf "ass={aligned_ass_path.as_posix()}"'
                 f' -c:v libx264 -preset fast -crf 23 -c:a copy "{final_output}"')
    
    if not ok or not final_output.exists():
        print("ERROR: Burning subtitles failed!")
        return

    final_dur = get_dur(final_output)
    kb = os.path.getsize(final_output) // 1024
    print(f"\nDone! Final video: {final_output} ({final_dur:.1f}s, {kb}KB)")

if __name__ == "__main__":
    asyncio.run(main_async())
