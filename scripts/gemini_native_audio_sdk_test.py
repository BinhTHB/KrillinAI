#!/usr/bin/env python3
"""
Test Gemini 2.5 Flash Native Audio Live Translation with TranslationConfig.
Send 15s Chinese audio, get Vietnamese audio back.
"""
import re
import os
import asyncio
import subprocess
from pathlib import Path

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


def load_api_key():
    text = Path("config/config.toml").read_text(encoding="utf-8")
    return re.search(r'api_key\s*=\s*"([^"]+)"', text).group(1)


def run(cmd):
    print("$", cmd[:200])
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:])


async def main():
    workdir = Path("tasks/douyin-test")
    video = workdir / "origin_video.mp4"
    pcm = workdir / "sdk_live_translate.pcm"
    out_wav = workdir / "sdk_live_translate.wav"
    out_txt = workdir / "sdk_live_translate.txt"

    print("Extract 15s audio...")
    run(f'ffmpeg -y -ss 0 -t 15 -i "{video}" -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le "{pcm}"')

    api = load_api_key()
    client = genai.Client(api_key=api, http_options={"api_version": "v1alpha"})

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        translation_config=types.TranslationConfig(
            target_language_code="vi-VN",
            # echo_target_language=False,
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            ),

        ),
        system_instruction="Dịch audio tiếng Trung ở đầu vào sang tiếng Việt. Chỉ nói phần dịch.",
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                silence_duration_ms=800,
                prefix_padding_ms=100,
            ),
        ),
    )

    print("Connecting", MODEL)
    audio = pcm.read_bytes()
    received_audio = bytearray()
    transcript = []

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("Sending audio in realtime-input chunks...")

        # Send via send_realtime_input (for VAD-driven response)
        chunk_size = 32000
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            await session.send_realtime_input(
                audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
            )
            await asyncio.sleep(len(chunk) / 32000)  # pace near real-time

        # Signal end of audio stream
        await session.send_realtime_input(audio_stream_end=True)

        print("Receiving translated audio...")
        async for msg in session.receive():
            if msg.data:
                received_audio.extend(msg.data)
                print(".", end="", flush=True)
            if msg.text:
                transcript.append(msg.text)
                print("\nTEXT:", msg.text[:200])
            if msg.server_content and msg.server_content.turn_complete:
                print("\nTurn complete")
                break
            if msg.server_content and msg.server_content.interrupted:
                print("\nInterrupted")

    print()
    if not received_audio:
        print("NO AUDIO RECEIVED")
        if transcript:
            print("Transcript only:", "".join(transcript))
        return

    # Convert 24kHz PCM to WAV
    out_pcm = workdir / "sdk_live_translate_raw.pcm"
    out_pcm.write_bytes(received_audio)
    run(f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{out_pcm}" "{out_wav}"')
    print(f"Audio saved: {out_wav}, {out_wav.stat().st_size} bytes, {len(received_audio)//48000:.1f}s")

    if transcript:
        out_txt.write_text("\n".join(transcript), encoding="utf-8")
        print(f"Transcript saved: {out_txt}")


if __name__ == "__main__":
    asyncio.run(main())

