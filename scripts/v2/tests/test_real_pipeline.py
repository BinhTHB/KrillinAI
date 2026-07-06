#!/usr/bin/env python3
"""Real integration smoke test for available credentials.

Loads local .env and config/config.toml without printing secrets.
Tests R2, Gemini, and FFmpeg. Skips missing credential areas.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_local_credentials() -> None:
    dot_env = Path(".env")
    if dot_env.exists():
        for line in dot_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

    toml = Path("config/config.toml")
    if toml.exists():
        in_llm = False
        for raw in toml.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line == "[llm]":
                in_llm = True
                continue
            if in_llm and line.startswith("["):
                break
            if in_llm and line.startswith("api_key") and "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    os.environ.setdefault("GEMINI_API_KEY", value)
                break


load_local_credentials()
os.environ.setdefault("KRILLINAI_DRY_RUN", "false")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.1-flash-lite")

from config import load_config

cfg = load_config()
passed = 0
failed = 0


def ok(label: str) -> None:
    global passed
    passed += 1
    print(f"  OK  {label}")


def fail(label: str, error: object) -> None:
    global failed
    failed += 1
    print(f"  ERR {label}: {str(error)[:220]}")


print("\n=== Real R2 ===")
if not all([cfg.r2_access_key_id, cfg.r2_secret_access_key, cfg.r2_endpoint, cfg.r2_bucket]):
    fail("R2 ops", "credentials missing")
else:
    try:
        from r2_client import R2Client

        r2 = R2Client()
        key = f"integration-test/hello-{int(time.time())}.txt"
        up = Path("workdir/integration-r2-up.txt")
        down = Path("workdir/integration-r2-down.txt")
        up.parent.mkdir(parents=True, exist_ok=True)
        up.write_text("hello real r2\n", encoding="utf-8")
        r2.upload_file(str(up), key)
        ok("upload_file")
        assert r2.exists(key)
        ok("exists")
        r2.download_file(key, str(down))
        assert down.read_text(encoding="utf-8") == "hello real r2\n"
        ok("download_file round-trip")
        r2._s3_client().delete_object(Bucket=cfg.r2_bucket, Key=key)
        ok("cleanup deleted")
    except Exception as exc:
        fail("R2 ops", exc)

print("\n=== Real Gemini Translation ===")
if not cfg.gemini_api_key:
    fail("Gemini translate", "GEMINI_API_KEY missing")
else:
    try:
        from gemini_client import GeminiClient

        text = "1\n00:00:01,000 --> 00:00:03,000\nHello, how are you?\n"
        translated = GeminiClient().translate_srt(text, "vi")
        assert "-->" in translated and "1" in translated
        ok("translate_srt preserves SRT structure")
        print("  sample:", translated.strip().replace("\n", " ")[:100])
    except Exception as exc:
        fail("Gemini translate", exc)

print("\n=== Real Gemini TTS ===")
if not cfg.gemini_api_key:
    fail("Gemini TTS", "GEMINI_API_KEY missing")
else:
    try:
        from gemini_client import GeminiClient

        audio = GeminiClient().synthesize_voice("Xin chào, đây là bài kiểm tra.", voice="Puck")
        assert len(audio) > 1000
        ok(f"synthesize_voice returns {len(audio)} bytes")
    except Exception as exc:
        fail("Gemini TTS", exc)

print("\n=== Real FFmpeg Render ===")
try:
    smoke = Path("workdir/real-smoke")
    smoke.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
        "-f", "lavfi", "-i", "sine=f=440:d=2", "-c:v", "libx264", "-c:a", "aac", str(smoke / "vid.mp4")
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=1000:d=2", "-c:a", "pcm_s16le", str(smoke / "tts.wav")
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (smoke / "sub.srt").write_text("1\n00:00:00,000 --> 00:00:01,500\nXin chào thế giới\n", encoding="utf-8")

    from render_ffmpeg import render_video

    render_video(smoke / "vid.mp4", smoke / "sub.srt", smoke / "tts.wav", smoke / "final.mp4")
    assert (smoke / "final.mp4").stat().st_size > 0
    ok("render_video produces output file")
except Exception as exc:
    fail("FFmpeg render", exc)

print("\n" + "=" * 40)
print(f"Results: {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
