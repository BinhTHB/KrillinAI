#!/usr/bin/env python3
"""
Controlled text-to-speech segment freezing pipeline.

Goal: output video where subtitle text, Vietnamese TTS audio, and source video scenes stay aligned.

Inputs:
  - origin_video.mp4
  - target-language SRT whose timestamps anchor source scenes

Method:
  - Merge too-short SRT entries into natural chunks.
  - Generate TTS (using Gemini Live API, Edge-TTS, or Hybrid) from the exact subtitle text.
  - Measure real TTS duration.
  - Speed up lightly, then freeze each source-video chunk if TTS is longer.
  - Build a new actual timeline and generate ASS/SRT aligned to the final video.
"""

import argparse
import asyncio
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Try to import SDK and Edge-TTS
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("WARN: google-genai not installed. Gemini provider won't be available.")
    genai = None

try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)


@dataclass
class Entry:
    index: int
    start: float
    end: float
    text: str


@dataclass
class Chunk:
    entries: list[Entry]
    index: int
    start: float = field(init=False)
    end: float = field(init=False)
    text: str = field(init=False)
    actual_start: float = 0.0
    actual_end: float = 0.0
    tts_duration: float = 0.0
    final_duration: float = 0.0
    freeze_duration: float = 0.0

    def __post_init__(self):
        self.start = self.entries[0].start
        self.end = self.entries[-1].end
        # Merge entries preserving punctuation at boundaries
        text_parts = []
        for e in self.entries:
            t = e.text.strip()
            if not t:
                continue
            # Capitalize first letter of each entry for consistent sentence start
            t = t[0].upper() + t[1:] if len(t) > 1 else t
            # Ensure each entry ends with some punctuation for TTS natural pacing
            if not t.endswith(('.', '?', '!', '…', ',', ';', ':')):
                t += '.'
            text_parts.append(t)
        self.text = " ".join(text_parts)

    @property
    def source_duration(self):
        return max(0.01, self.end - self.start)

    @property
    def normalized_tts_text(self):
        # Return cleaned text. Multiple punctuation marks normalized.
        text = self.text.strip()
        # Clean double dots or spacing around punctuation
        text = re.sub(r'\s+([.,!?…;:])', r'\1', text)
        text = re.sub(r'\.+', '.', text)
        return text


def run_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {cmd}", flush=True)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip()[-2000:]
        raise RuntimeError(f"Command failed ({result.returncode}): {cmd}\n{stderr}")
    return result


def get_duration(path: Path) -> float:
    result = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "{path}"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def safe_rmtree(path: Path, retries: int = 5):
    for attempt in range(1, retries + 1):
        try:
            if path.exists():
                shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == retries:
                raise
            time.sleep(1)


def ensure_media(path: Path, label: str, min_duration: float = 0.05) -> float:
    if not path.exists():
        raise RuntimeError(f"Missing {label}: {path}")
    duration = get_duration(path)
    if duration < min_duration:
        raise RuntimeError(f"Invalid {label}: {path} duration={duration:.3f}s")
    return duration


def parse_time(value: str) -> float:
    h, m, s = value.strip().replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def format_srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    ms = int(round((sec - int(sec)) * 1000))
    whole = int(sec)
    if ms == 1000:
        whole += 1
        ms = 0
    h = whole // 3600
    m = (whole % 3600) // 60
    s = whole % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    cs = int(round((sec - int(sec)) * 100))
    whole = int(sec)
    if cs == 100:
        whole += 1
        cs = 0
    h = whole // 3600
    m = (whole % 3600) // 60
    s = whole % 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def parse_srt(path: Path) -> list[Entry]:
    content = path.read_text(encoding='utf-8-sig', errors='ignore')
    blocks = [b for b in re.split(r'\n\s*\n', content.strip()) if b.strip()]
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or '-->' not in lines[1]:
            continue
        try:
            idx = int(re.sub(r'\D+', '', lines[0]) or len(entries) + 1)
            start_s, end_s = [part.strip() for part in lines[1].split('-->')]
            text = ' '.join(lines[2:]).strip()
            if not text or '[Translation failed' in text:
                continue
            entries.append(Entry(index=idx, start=parse_time(start_s), end=parse_time(end_s), text=text))
        except Exception:
            continue
    entries.sort(key=lambda item: (item.start, item.end, item.index))
    return entries


def merge_entries(entries: list[Entry], min_chunk: float, max_chunk: float, max_chars: int) -> list[Chunk]:
    raw_chunks: list[list[Entry]] = []
    current: list[Entry] = []
    for entry in entries:
        candidate = current + [entry]
        duration = candidate[-1].end - candidate[0].start
        chars = len(' '.join(e.text for e in candidate))
        current_duration = current[-1].end - current[0].start if current else 0.0
        should_close = False
        if current and current_duration >= min_chunk:
            if duration > max_chunk or chars > max_chars:
                should_close = True
            elif entry.text.endswith(('.', '?', '!', '…')):
                should_close = True
        if should_close:
            raw_chunks.append(current)
            current = [entry]
        else:
            current = candidate
    if current:
        raw_chunks.append(current)

    # Post-pass: eliminate orphan chunks shorter than min_chunk
    merged: list[list[Entry]] = []
    i = 0
    while i < len(raw_chunks):
        group = raw_chunks[i]
        duration = group[-1].end - group[0].start
        if duration < min_chunk and i + 1 < len(raw_chunks):
            nxt = raw_chunks[i + 1]
            candidate = group + nxt
            candidate_duration = candidate[-1].end - candidate[0].start
            candidate_chars = len(' '.join(e.text for e in candidate))
            if candidate_duration <= max_chunk + min_chunk and candidate_chars <= max_chars * 2:
                merged.append(candidate)
                i += 2
                continue
        if duration < min_chunk and merged:
            prev = merged.pop()
            merged.append(prev + group)
        else:
            merged.append(group)
        i += 1

    return [Chunk(entries=group, index=i + 1) for i, group in enumerate(merged)]


def load_api_key() -> str:
    config_path = Path("config/config.toml")
    if not config_path.exists():
        return ""
    content = config_path.read_text(encoding="utf-8")
    match = re.search(r'api_key\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else ""


async def edge_tts_text(text: str, output_mp3: Path, voice: str, rate: str, retries: int = 5) -> bool:
    for attempt in range(1, retries + 1):
        try:
            if output_mp3.exists():
                output_mp3.unlink()
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await communicate.save(str(output_mp3))
            if output_mp3.exists() and output_mp3.stat().st_size > 1000:
                return True
        except Exception as exc:
            print(f"  Edge-TTS retry {attempt}/{retries}: {exc}", flush=True)
            await asyncio.sleep(2)
    return False


async def gemini_tts_text(text: str, output_wav: Path, api_key: str, voice_name: str = "Puck", retries: int = 3) -> bool:
    if not genai or not api_key:
        return False

    GEMINI_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
    GEMINI_API_VERSION = "v1alpha"

    # Configure connection. Puck has standard natural voice style.
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            ),
            language_code="vi-VN",
        ),
        system_instruction=(
            "Hãy đọc to đoạn văn sau bằng tiếng Việt với giọng đọc diễn cảm, tự nhiên, đúng sắc thái. "
            "Tuyệt đối chỉ trả về âm thanh giọng đọc tiếng Việt của đoạn văn đó. "
            "Không thêm lời bình luận, không nói bất kỳ câu dẫn nào khác."
        ),
    )

    for attempt in range(1, retries + 1):
        try:
            if output_wav.exists():
                output_wav.unlink()
            
            client = genai.Client(api_key=api_key, http_options={"api_version": GEMINI_API_VERSION})
            received_audio = bytearray()
            
            async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
                # Send the text to be read aloud
                await session.send(input=text, end_of_turn=True)
                
                # Receive the audio PCM 24kHz stream
                async for msg in session.receive():
                    if msg.data:
                        received_audio.extend(msg.data)
                    if msg.server_content and msg.server_content.turn_complete:
                        break
            
            if received_audio:
                # Convert raw 24kHz 16-bit mono PCM bytes to WAV
                temp_pcm = output_wav.with_suffix('.raw.pcm')
                temp_pcm.write_bytes(bytes(received_audio))
                run_cmd(f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{temp_pcm}" -ac 1 -ar 44100 "{output_wav}"')
                try:
                    temp_pcm.unlink()
                except:
                    pass
                if output_wav.exists() and get_duration(output_wav) > 0.05:
                    return True
        except Exception as exc:
            print(f"  Gemini-TTS retry {attempt}/{retries}: {exc}", flush=True)
            await asyncio.sleep(2)
            
    return False


def write_ass(path: Path, chunks: list[Chunk], width: int = 1280, height: int = 720):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3.0,1.0,2,20,20,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header.rstrip()]
    for chunk in chunks:
        text = chunk.text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('\n', ' ')
        lines.append(f"Dialogue: 0,{format_ass_time(chunk.actual_start)},{format_ass_time(chunk.actual_end)},Default,,0,0,0,,{{\\an2}}{text}")
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_srt(path: Path, chunks: list[Chunk]):
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        blocks.append(f"{i}\n{format_srt_time(chunk.actual_start)} --> {format_srt_time(chunk.actual_end)}\n{chunk.text}\n")
    path.write_text('\n'.join(blocks), encoding='utf-8')


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', default='tasks/douyin-test')
    parser.add_argument('--srt', default='target_language_srt_clean.srt')
    parser.add_argument('--video', default='origin_video.mp4')
    parser.add_argument('--output-dir', default='controlled_tts_freezing')
    parser.add_argument('--voice', default='vi-VN-HoaiMyNeural')
    parser.add_argument('--rate', default='+0%')
    parser.add_argument('--speed', type=float, default=1.25)
    parser.add_argument('--gap', type=float, default=0.05)
    parser.add_argument('--bg-volume', type=float, default=0.10)
    parser.add_argument('--min-chunk', type=float, default=2.5)
    parser.add_argument('--max-chunk', type=float, default=6.0)
    parser.add_argument('--max-chars', type=int, default=140)
    parser.add_argument('--max-chunks', type=int, default=0)
    parser.add_argument('--keep-cache', action='store_true')
    parser.add_argument('--tts-provider', default='hybrid', choices=['edge', 'gemini', 'hybrid'])
    parser.add_argument('--gemini-voice', default='Puck', choices=['Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede'])
    args = parser.parse_args()

    workdir = Path(args.workdir)
    video_path = workdir / args.video
    srt_path = workdir / args.srt
    out_dir = workdir / args.output_dir
    seg_dir = out_dir / 'segments'

    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not srt_path.exists():
        raise FileNotFoundError(srt_path)

    api_key = ""
    if args.tts_provider in ['gemini', 'hybrid']:
        api_key = load_api_key()
        if not api_key:
            print("WARN: No Gemini API Key found. Falling back to edge-tts.")
            args.tts_provider = 'edge'

    if out_dir.exists() and not args.keep_cache:
        safe_rmtree(out_dir)
    seg_dir.mkdir(parents=True, exist_ok=True)

    video_dur = get_duration(video_path)
    entries = parse_srt(srt_path)
    chunks = merge_entries(entries, args.min_chunk, args.max_chunk, args.max_chars)
    if args.max_chunks:
        chunks = chunks[:args.max_chunks]
    print(f"Input video: {video_path} ({video_dur:.2f}s)", flush=True)
    print(f"Input SRT: {srt_path} entries={len(entries)} chunks={len(chunks)}", flush=True)
    print(f"TTS Provider: {args.tts_provider}", flush=True)

    last_frame = out_dir / 'last_frame.png'
    run_cmd(f'ffmpeg -y -ss {max(0, video_dur - 1):.3f} -i "{video_path}" -frames:v 1 -update 1 "{last_frame}"')

    concat_file = out_dir / 'concat.txt'
    processed = []
    current = 0.0

    for chunk in chunks:
        print(f"\n[{chunk.index}/{len(chunks)}] {chunk.start:.2f}-{chunk.end:.2f}s src={chunk.source_duration:.2f}s", flush=True)
        print(f"  text: {chunk.text[:80]}", flush=True)
        
        prefix = seg_dir / f"chunk_{chunk.index:04d}"
        tts_raw = prefix.with_suffix('.tts_raw.wav')
        tts_wav = prefix.with_suffix('.tts.wav')
        tts_speed = prefix.with_suffix('.tts_speed.wav')
        v_src = prefix.with_suffix('.video.mp4')
        v_out = prefix.with_suffix('.video_frozen.mp4')
        a_bg = prefix.with_suffix('.bg.wav')
        a_mix = prefix.with_suffix('.mix.wav')
        combined = prefix.with_suffix('.combined.mp4')

        # Generate voiceover based on provider
        used_gemini = False
        tts_text_normalized = chunk.normalized_tts_text

        if args.tts_provider in ['gemini', 'hybrid']:
            print("  Generating voice via Gemini Live...", flush=True)
            ok = await gemini_tts_text(tts_text_normalized, tts_raw, api_key, args.gemini_voice)
            if ok:
                used_gemini = True
                print("  Gemini TTS OK.", flush=True)
            elif args.tts_provider == 'hybrid':
                print("  Gemini failed. Falling back to Edge-TTS...", flush=True)
                tmp_mp3 = prefix.with_suffix('.tts.mp3')
                ok = await edge_tts_text(tts_text_normalized, tmp_mp3, args.voice, args.rate)
                if ok:
                    run_cmd(f'ffmpeg -y -i "{tmp_mp3}" -ac 1 -ar 44100 "{tts_raw}"')
                    try:
                        tmp_mp3.unlink()
                    except:
                        pass
            else:
                ok = False
        else:
            # Edge-TTS
            tmp_mp3 = prefix.with_suffix('.tts.mp3')
            ok = await edge_tts_text(tts_text_normalized, tmp_mp3, args.voice, args.rate)
            if ok:
                run_cmd(f'ffmpeg -y -i "{tmp_mp3}" -ac 1 -ar 44100 "{tts_raw}"')
                try:
                    tmp_mp3.unlink()
                except:
                    pass

        if not ok or not tts_raw.exists():
            print(f"  SKIP chunk {chunk.index}: TTS generation failed", flush=True)
            continue
            
        shutil.copy2(tts_raw, tts_wav)
        ensure_media(tts_wav, 'raw TTS wav')
        
        # Adaptive speed: Gemini usually sounds better without speedup or with very light speedup.
        # Edge-TTS needs rate speedup. We apply speedup based on need.
        speed_factor = args.speed
        if used_gemini:
            # Faster adaptive Gemini pacing requested by user.
            # Keep expressive quality where possible, but cap long chunks at 1.30x to reduce dead air/freeze.
            est_factor = (get_duration(tts_wav) + args.gap) / chunk.source_duration
            if est_factor <= 1.05:
                speed_factor = 1.05
            elif est_factor <= 1.20:
                speed_factor = 1.15
            elif est_factor <= 1.40:
                speed_factor = 1.25
            else:
                speed_factor = 1.30
        
        if abs(speed_factor - 1.0) > 0.01:
            speed_result = run_cmd(f'ffmpeg -y -i "{tts_wav}" -filter:a "atempo={speed_factor:.3f}" -ac 1 -ar 44100 "{tts_speed}"', check=False)
            if speed_result.returncode != 0 or not tts_speed.exists() or get_duration(tts_speed) < 0.05:
                print("  WARN: speed conversion failed; using raw TTS", flush=True)
                shutil.copy2(tts_wav, tts_speed)
        else:
            shutil.copy2(tts_wav, tts_speed)

        tts_dur = ensure_media(tts_speed, 'speed-adjusted TTS')
        chunk.tts_duration = tts_dur
        final_dur = max(chunk.source_duration, tts_dur + args.gap)
        chunk.final_duration = final_dur
        chunk.freeze_duration = max(0.0, final_dur - chunk.source_duration)

        if chunk.start >= video_dur - 0.05:
            run_cmd(f'ffmpeg -y -loop 1 -i "{last_frame}" -t {final_dur:.3f} -pix_fmt yuv420p -r 30 -c:v libx264 -preset fast -crf 23 "{v_out}"')
            run_cmd(f'ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t {final_dur:.3f} "{a_bg}"')
        else:
            end = min(chunk.end, video_dur)
            run_cmd(f'ffmpeg -y -ss {chunk.start:.3f} -to {end:.3f} -i "{video_path}" -c:v libx264 -preset fast -crf 23 -an "{v_src}"')
            v_src_dur = get_duration(v_src)
            if final_dur > v_src_dur + 0.01:
                freeze = final_dur - v_src_dur
                run_cmd(f'ffmpeg -y -i "{v_src}" -vf "tpad=stop_mode=clone:stop_duration={freeze:.3f}" -c:v libx264 -preset fast -crf 23 "{v_out}"')
            else:
                shutil.copy2(v_src, v_out)
            run_cmd(f'ffmpeg -y -ss {chunk.start:.3f} -to {end:.3f} -i "{video_path}" -vn -ac 2 -ar 44100 -acodec pcm_s16le "{a_bg}"')

        samples = int(math.ceil(final_dur * 44100))
        run_cmd(
            f'ffmpeg -y -i "{a_bg}" -i "{tts_speed}" -filter_complex '
            f'"[0:a]volume={args.bg_volume:.3f},apad=whole_len={samples}[bg];'
            f'[1:a]volume=1.0,aformat=sample_rates=44100:channel_layouts=mono,apad=whole_len={samples}[voice];'
            f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
            f'-t {final_dur:.3f} -ac 2 -ar 44100 "{a_mix}"'
        )
        run_cmd(f'ffmpeg -y -i "{v_out}" -i "{a_mix}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -shortest "{combined}"')
        real_dur = get_duration(combined)
        chunk.actual_start = current
        chunk.actual_end = current + real_dur
        current = chunk.actual_end
        processed.append(chunk)
        print(f"  ok: tts={tts_dur:.2f}s final={real_dur:.2f}s freeze={chunk.freeze_duration:.2f}s timeline={current:.2f}s (provider={'gemini' if used_gemini else 'edge'})", flush=True)

    if not processed:
        raise RuntimeError('No chunks processed')

    with concat_file.open('w', encoding='utf-8') as f:
        for chunk in processed:
            p = (seg_dir / f"chunk_{chunk.index:04d}.combined.mp4").resolve().as_posix()
            f.write(f"file '{p}'\n")

    concat_raw = out_dir / 'controlled_concat_raw.mp4'
    final_mp4 = out_dir / 'controlled_tts_final.mp4'
    ass_path = out_dir / 'controlled_aligned.ass'
    srt_out = out_dir / 'controlled_aligned.srt'

    print('\nConcatenating chunks...', flush=True)
    run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{concat_raw}"')
    write_ass(ass_path, processed)
    write_srt(srt_out, processed)
    print('Burning subtitles...', flush=True)
    run_cmd(f'ffmpeg -y -i "{concat_raw}" -vf "ass={ass_path.as_posix()}" -c:v libx264 -preset fast -crf 23 -c:a copy "{final_mp4}"')

    print('\nDONE', flush=True)
    print(f"  video: {final_mp4}", flush=True)
    print(f"  ass:   {ass_path}", flush=True)
    print(f"  srt:   {srt_out}", flush=True)
    print(f"  duration: {get_duration(final_mp4):.2f}s", flush=True)
    print(f"  chunks: {len(processed)}/{len(chunks)}", flush=True)


if __name__ == '__main__':
    asyncio.run(main())
