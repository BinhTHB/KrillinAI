#!/usr/bin/env python3
"""Unit tests for GeminiClient dry-run mode."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

os.environ["KRILLINAI_DRY_RUN"] = "true"

from gemini_client import GeminiClient


def test_translate_srt_dry_run() -> None:
    client = GeminiClient()
    srt = "1\n00:00:00,000 --> 00:00:01,000\n[Dry run] Hello\n"
    translated = client.translate_srt(srt, "vi")
    assert "[Dry run translated]" in translated
    assert "00:00:00,000 --> 00:00:01,000" in translated


def test_synthesize_voice_dry_run_returns_audio_bytes() -> None:
    client = GeminiClient()
    audio = client.synthesize_voice("Xin chào")
    assert audio == b"KRILLINAI_DRY_RUN_GEMINI_TTS"


if __name__ == "__main__":
    test_translate_srt_dry_run()
    test_synthesize_voice_dry_run_returns_audio_bytes()
    print("All Gemini client tests passed.")
