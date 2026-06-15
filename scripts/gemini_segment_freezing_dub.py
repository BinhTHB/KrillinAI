#!/usr/bin/env python3
"""
Segment-level Gemini Native Audio dubbing with local video freezing and aligned subtitles.

Pipeline:
  1. Parse Vietnamese SRT for segment timing and subtitle text.
  2. Cut the original Chinese audio per SRT segment.
  3. Send each audio segment to Gemini Live Translation (zh audio -> vi speech).
  4. Measure Gemini audio duration and freeze only that segment when speech is longer.
  5. Mix original segment audio at 15% + Gemini speech at 100%.
  6. Concatenate segments and burn a single ASS subtitle file using the final timeline.
"""
import argparse
import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_API_VERSION = "v1alpha"


def run_cmd(cmd, verbose=True, check=False):
    if verbose:
        print(f"  $ {cmd[:240]}", flush=True)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[-1200:]
        if verbose:
            print(f"  WARN rc={result.returncode}: {err}", flush=True)
        if check:
            raise RuntimeError(err)
        return False
    return True


def get_dur(path):
    r = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "{path}"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def load_api_key():
    text = Path("config/config.toml").read_text(encoding="utf-8")
    match = re.search(r'api_key\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("No api_key found in config/config.toml")
    return match.group(1)


def parse_srt_time(value):
    h, m, rest = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def format_srt_time(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_ass_time(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def parse_srt(path):
    content = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n+", content.strip())
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        timing_idx = None
        for i, line in enumerate(lines):
            if "-->" in line:
                timing_idx = i
                break
        if timing_idx is None:
            continue
        start_s, end_s = [x.strip() for x in lines[timing_idx].split("-->")]
        text = " ".join(lines[timing_idx + 1 :]).strip()
        if not text:
            continue
        entries.append({
            "idx": len(entries) + 1,
            "start": parse_srt_time(start_s),
            "end": parse_srt_time(end_s),
            "text": text,
        })
    return entries


def ass_escape(text):
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", " ")


def write_aligned_ass(path, entries, width=1280, height=720):
    fontsize = 36 if height <= 720 else 42
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,3.0,1.0,2,40,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for entry in entries:
        lines.append(
            f"Dialogue: 0,{format_ass_time(entry['actual_start'])},{format_ass_time(entry['actual_end'])},Default,,0,0,0,,{{\\an2}}{ass_escape(entry['text'])}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_aligned_srt(path, entries):
    blocks = []
    for i, entry in enumerate(entries, 1):
        blocks.append(
            f"{i}\n{format_srt_time(entry['actual_start'])} --> {format_srt_time(entry['actual_end'])}\n{entry['text']}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


class GeminiSegmentTranslator:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key, http_options={"api_version": GEMINI_API_VERSION})
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            translation_config=types.TranslationConfig(target_language_code="vi-VN"),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                ),
                language_code="vi-VN",
            ),
            system_instruction=(
                "Dịch audio tiếng Trung sang tiếng Việt và chỉ đọc bản dịch tiếng Việt. "
                "Không giải thích, không thêm lời dẫn, không trả lời bằng chữ."
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    silence_duration_ms=500,
                    prefix_padding_ms=80,
                ),
            ),
        )

    async def translate_pcm_to_wav(self, pcm_path, wav_path, raw_pcm_path):
        audio = pcm_path.read_bytes()
        received = bytearray()
        async with self.client.aio.live.connect(model=GEMINI_MODEL, config=self.config) as session:
            chunk_size = 32000
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i : i + chunk_size]
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(len(chunk) / 32000)
            await session.send_realtime_input(audio_stream_end=True)

            try:
                async with asyncio.timeout(20):
                    async for msg in session.receive():
                        if msg.data:
                            received.extend(msg.data)
                        if msg.server_content and msg.server_content.interrupted:
                            break
                        if msg.server_content and msg.server_content.turn_complete:
                            break
            except TimeoutError:
                pass

        if not received:
            return False
        raw_pcm_path.write_bytes(received)
        ok = run_cmd(
            f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{raw_pcm_path}" "{wav_path}"',
            verbose=False,
        )
        return ok and wav_path.exists() and get_dur(wav_path) > 0.05


async def main_async():
    parser = argparse.ArgumentParser(description="Segment Gemini Native Audio dubbing with aligned ASS subtitles")
    parser.add_argument("--workdir", default="tasks/douyin-test")
    parser.add_argument("--srt", default="target_language_srt_clean.srt")
    parser.add_argument("--video", default="origin_video.mp4")
    parser.add_argument("--max-segments", type=int, default=0, help="Process only first N segments for testing")
    parser.add_argument("--start-segment", type=int, default=1)
    parser.add_argument("--bg-volume", type=float, default=0.15)
    parser.add_argument("--gap", type=float, default=0.15)
    args = parser.parse_args()

    workdir = Path(args.workdir)
    video_path = workdir / args.video
    srt_path = workdir / args.srt
    out_dir = workdir / "gemini_segment_freezing"
    seg_dir = out_dir / "segments"

    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not srt_path.exists():
        raise FileNotFoundError(srt_path)

    entries = parse_srt(srt_path)
    entries = [e for e in entries if e["idx"] >= args.start_segment]
    if args.max_segments > 0:
        entries = entries[: args.max_segments]
    if not entries:
        raise RuntimeError("No SRT entries selected")

    if out_dir.exists():
        try:
            shutil.rmtree(out_dir)
        except Exception:
            # Fallback: ignore or reuse
            pass
    seg_dir.mkdir(parents=True, exist_ok=True)

    video_dur = get_dur(video_path)
    print(f"Video: {video_path} ({video_dur:.2f}s)")
    print(f"SRT: {srt_path} | selected segments: {len(entries)}")

    api_key = load_api_key()
    gemini = GeminiSegmentTranslator(api_key)

    last_frame = out_dir / "last_frame.png"
    run_cmd(
        f'ffmpeg -y -ss {max(0, video_dur - 1.0):.3f} -i "{video_path}" '
        f'-frames:v 1 -update 1 "{last_frame}"'
    )

    concat_file = out_dir / "concat.txt"
    processed = []
    current_timeline = 0.0

    for n, entry in enumerate(entries, 1):
        idx = entry["idx"]
        start = entry["start"]
        end = min(entry["end"], video_dur)
        orig_dur = max(0.05, end - start)
        prefix = seg_dir / f"seg_{idx:04d}"
        src_pcm = prefix.with_suffix(".src.pcm")
        gem_raw = prefix.with_suffix(".gemini.raw.pcm")
        gem_wav = prefix.with_suffix(".gemini.wav")
        v_cut = prefix.with_suffix(".video.mp4")
        v_final = prefix.with_suffix(".video_final.mp4")
        a_bg = prefix.with_suffix(".bg.wav")
        a_mix = prefix.with_suffix(".mix.wav")
        combined = prefix.with_suffix(".combined.mp4")

        print(f"\n[{n}/{len(entries)}] #{idx} {start:.2f}-{end:.2f}s | {entry['text'][:70]}", flush=True)

        # Extract source audio segment as 16kHz PCM for Gemini.
        run_cmd(
            f'ffmpeg -y -ss {start:.3f} -t {orig_dur:.3f} -i "{video_path}" '
            f'-vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le "{src_pcm}"',
            verbose=False,
            check=True,
        )

        ok = False
        for attempt in range(1, 4):
            try:
                ok = await gemini.translate_pcm_to_wav(src_pcm, gem_wav, gem_raw)
            except Exception as e:
                print(f"  Gemini attempt {attempt}/3 failed: {e}", flush=True)
                ok = False
            if ok:
                break
            await asyncio.sleep(2)
        if not ok:
            print(f"  SKIP #{idx}: no Gemini audio", flush=True)
            continue

        gem_dur = get_dur(gem_wav)
        final_dur = max(orig_dur, gem_dur + args.gap)
        freeze_dur = max(0.0, final_dur - orig_dur)

        if start >= video_dur - 0.05:
            run_cmd(
                f'ffmpeg -y -loop 1 -i "{last_frame}" -t {final_dur:.3f} '
                f'-pix_fmt yuv420p -c:v libx264 -preset fast -crf 23 -r 30 "{v_final}"',
                verbose=False,
                check=True,
            )
            run_cmd(
                f'ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t {final_dur:.3f} "{a_bg}"',
                verbose=False,
                check=True,
            )
        else:
            run_cmd(
                f'ffmpeg -y -ss {start:.3f} -t {orig_dur:.3f} -i "{video_path}" '
                f'-an -c:v libx264 -preset fast -crf 23 "{v_cut}"',
                verbose=False,
                check=True,
            )
            if freeze_dur > 0.01:
                run_cmd(
                    f'ffmpeg -y -i "{v_cut}" -vf "tpad=stop_mode=clone:stop_duration={freeze_dur:.3f}" '
                    f'-c:v libx264 -preset fast -crf 23 "{v_final}"',
                    verbose=False,
                    check=True,
                )
            else:
                shutil.copy2(v_cut, v_final)
            run_cmd(
                f'ffmpeg -y -ss {start:.3f} -t {orig_dur:.3f} -i "{video_path}" '
                f'-vn -acodec pcm_s16le -ar 44100 -ac 2 "{a_bg}"',
                verbose=False,
                check=True,
            )

        pad_samples = max(1, int(final_dur * 44100))
        run_cmd(
            f'ffmpeg -y -i "{a_bg}" -i "{gem_wav}" -filter_complex '
            f'"[0:a]volume={args.bg_volume},apad=whole_len={pad_samples}[bg];'
            f'[1:a]aformat=sample_rates=44100:channel_layouts=mono,apad=whole_len={pad_samples}[voice];'
            f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
            f'-ac 2 -ar 44100 "{a_mix}"',
            verbose=False,
            check=True,
        )

        run_cmd(
            f'ffmpeg -y -i "{v_final}" -i "{a_mix}" -c:v libx264 -preset fast -crf 23 '
            f'-c:a aac -b:a 192k -shortest "{combined}"',
            verbose=False,
            check=True,
        )

        comb_dur = get_dur(combined)
        entry["actual_start"] = current_timeline
        entry["actual_end"] = current_timeline + comb_dur
        entry["gemini_audio_dur"] = gem_dur
        entry["final_dur"] = comb_dur
        current_timeline += comb_dur
        processed.append(entry)
        print(
            f"  ok: orig={orig_dur:.2f}s gemini={gem_dur:.2f}s freeze={freeze_dur:.2f}s final={comb_dur:.2f}s timeline={current_timeline:.2f}s",
            flush=True,
        )

    if not processed:
        raise RuntimeError("No segments processed")

    with concat_file.open("w", encoding="utf-8") as f:
        for entry in processed:
            combined = (seg_dir / f"seg_{entry['idx']:04d}.combined.mp4").resolve().as_posix()
            f.write(f"file '{combined}'\n")

    concat_raw = out_dir / "concat_raw.mp4"
    output_ass = out_dir / "gemini_segment_aligned.ass"
    output_srt = out_dir / "gemini_segment_aligned.srt"
    output_video = out_dir / "gemini_segment_final.mp4"

    print("\nConcatenating segments...")
    run_cmd(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{concat_raw}"',
        check=True,
    )

    write_aligned_ass(output_ass, processed)
    write_aligned_srt(output_srt, processed)

    print("Burning aligned subtitles...")
    ass_filter_path = output_ass.as_posix()
    run_cmd(
        f'ffmpeg -y -i "{concat_raw}" -vf "ass={ass_filter_path}" -c:v libx264 -preset fast -crf 23 -c:a copy "{output_video}"',
        check=True,
    )

    print("\nDONE")
    print(f"  video: {output_video}")
    print(f"  ass:   {output_ass}")
    print(f"  srt:   {output_srt}")
    print(f"  duration: {get_dur(output_video):.2f}s")
    print(f"  segments: {len(processed)}/{len(entries)}")


if __name__ == "__main__":
    asyncio.run(main_async())
