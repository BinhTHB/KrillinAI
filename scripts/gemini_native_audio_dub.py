#!/usr/bin/env python3
"""
Translate and dub video from Chinese to Vietnamese using Gemini 2.5 Flash Native Audio Live Translation.
Uses google-genai SDK for robust connection.
"""
import re
import os
import sys
import asyncio
import argparse
import subprocess
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import types

# Use the verified Gemini model and API version
GEMINI_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_API_VERSION = "v1alpha"


def load_api_key():
    config_path = Path("config/config.toml")
    if not config_path.exists():
        print("ERROR: config/config.toml not found")
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'api_key\s*=\s*"([^"]+)"', content)
    if match:
        key = match.group(1)
        if key and len(key) > 10:
            return key
    print("ERROR: No valid API key in config")
    return None


def run_cmd(cmd, verbose=True):
    if verbose:
        print(f"  $ {cmd[:200]}")
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        err = result.stderr.strip()[:500]
        if verbose:
            print(f"  WARN (rc={result.returncode}): {err}")
        return False
    return True


def get_dur(path):
    r = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{path}"',
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        val = r.stdout.strip()
        return float(val) if val else 0.0
    except:
        return 0.0


async def translate_audio_sdk(api_key, input_pcm, system_prompt):
    """Call Gemini Live API via Python SDK for native audio translation."""
    client = genai.Client(api_key=api_key, http_options={"api_version": GEMINI_API_VERSION})

    # Configure live connection with translation + speech details
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        translation_config=types.TranslationConfig(
            target_language_code="vi-VN",
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            ),

        ),
        system_instruction=system_prompt,
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                silence_duration_ms=800,
                prefix_padding_ms=100,
            ),
        ),
    )

    audio_data = input_pcm.read_bytes()
    received_audio = bytearray()
    received_text = []

    print("[Connecting to Gemini Live API via SDK...]")
    async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
        print(
            f"[Sending audio in realtime chunks: {len(audio_data)} bytes ({len(audio_data)/(16000*2):.1f}s)]"
        )
        chunk_size = 32000  # 1s chunk of 16kHz 16-bit mono
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            await session.send_realtime_input(
                audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
            )
            # Pace audio close to real time so Live API VAD can group turns correctly
            await asyncio.sleep(len(chunk) / 32000)

        # Signal end of stream
        await session.send_realtime_input(audio_stream_end=True)

        print("[Receiving translated audio response...]")
        async for msg in session.receive():
            if msg.data:
                received_audio.extend(msg.data)
            if msg.text:
                received_text.append(msg.text)
                print(f"  Transcript: {msg.text[:200]}")
            if msg.server_content and msg.server_content.turn_complete:
                print("[Turn complete]")
                break
            if msg.server_content and msg.server_content.interrupted:
                print("[Interrupted]")

    return bytes(received_audio), "".join(received_text)


async def main_async():
    parser = argparse.ArgumentParser(description="Gemini Native Audio Dialog Dub")
    parser.add_argument(
        "--test-short",
        type=int,
        default=0,
        help="Only process first N seconds of video for quick test",
    )
    parser.add_argument(
        "--workdir",
        type=str,
        default="tasks/douyin-test",
        help="Working directory with origin_video.mp4",
    )
    parser.add_argument(
        "--system-prompt", type=str, default=None, help="System instruction override"
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        default=True,
        help="Also create combined video with audio output (default: True)",
    )
    args = parser.parse_args()

    workdir = Path(args.workdir)
    video_path = workdir / "origin_video.mp4"

    if not video_path.exists():
        print(f"ERROR: {video_path} not found")
        return

    video_dur = get_dur(video_path)
    print(f"Input video: {video_path}")
    print(f"  Duration: {video_dur:.2f}s")
    if args.test_short > 0:
        print(f"  TEST MODE: using first {args.test_short}s only")
        video_dur = min(video_dur, args.test_short)

    api_key = load_api_key()
    if not api_key:
        return

    system_prompt = args.system_prompt or (
        "Dịch toàn bộ audio tiếng Trung của video này sang tiếng Việt. "
        "Hãy đọc bản dịch bằng tiếng Việt với giọng đọc tự nhiên, truyền cảm. "
        "Tuyệt đối chỉ trả về âm thanh tiếng Việt, không giải thích, không trò chuyện."
    )

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_audio_", dir=workdir))

    # Step 1: Extract audio as 16kHz PCM
    print("\n=== Step 1: Extract audio as 16kHz PCM ===")
    pcm_path = tmp_dir / "input.pcm"

    if args.test_short > 0:
        cmd = (
            f'ffmpeg -y -ss 0 -t {args.test_short} -i "{video_path}" '
            f'-vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le "{pcm_path}"'
        )
    else:
        cmd = f'ffmpeg -y -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le "{pcm_path}"'

    if not run_cmd(cmd):
        print("ERROR: Audio extraction failed")
        return

    # Step 2: Send to Gemini Live API
    print(f"\n=== Step 2: Gemini Native Audio Dialog (SDK) ===")
    try:
        audio_out, text_out = await translate_audio_sdk(api_key, pcm_path, system_prompt)
    except Exception as e:
        print(f"ERROR: Live API session failed: {e}")
        import traceback

        traceback.print_exc()
        return
    finally:
        # Clean up temp
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)

    if not audio_out:
        print("ERROR: No audio response received from Gemini!")
        return

    # Step 3: Save audio output
    print(f"\n=== Step 3: Save audio output ===")
    output_wav = workdir / "gemini_native_audio.wav"
    output_pcm = workdir / "gemini_native_audio_raw.pcm"
    output_pcm.write_bytes(audio_out)

    # Convert 24kHz PCM from Gemini to WAV
    run_cmd(f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{output_pcm}" "{output_wav}"')
    if output_pcm.exists():
        output_pcm.unlink()

    output_dur = len(audio_out) / (24000 * 2)
    print(f"  Saved: {output_wav}")
    print(f"  Duration: {output_dur:.1f}s")
    if text_out:
        transcript_path = workdir / "gemini_native_transcript.txt"
        transcript_path.write_text(text_out, encoding="utf-8")
        print(f"  Transcript: {text_out[:200]}...")
        print(f"  Transcript saved: {transcript_path}")

    # Step 4: Combine with video
    if args.combine:
        print(f"\n=== Step 4: Combine with video ===")
        output_video = workdir / "gemini_native_video.mp4"
        if output_dur > video_dur:
            extra = output_dur - video_dur
            cmd = (
                f'ffmpeg -y -ss 0 -t {video_dur} -i "{video_path}" -i "{output_wav}" '
                f'-filter_complex "[0:v]tpad=stop_mode=clone:stop_duration={extra:.3f}[v]" '
                f'-map "[v]" -map 1:a -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{output_video}"'
            )
        else:
            cmd = (
                f'ffmpeg -y -ss 0 -t {video_dur} -i "{video_path}" -i "{output_wav}" '
                f'-c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -shortest "{output_video}"'
            )
        run_cmd(cmd)
        if output_video.exists():
            print(f"  Combined video: {output_video}")

    print(f"\n{'='*60}")
    print(f"DONE! Output: {output_wav}")
    print(f"  Audio duration: {output_dur:.1f}s (original video: {video_dur:.1f}s)")
    print(f"  Ratio: {output_dur/max(video_dur, 0.1):.2f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main_async())

