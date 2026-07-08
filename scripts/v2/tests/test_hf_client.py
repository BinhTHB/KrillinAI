#!/usr/bin/env python3
"""Unit tests for HuggingFaceClient ? dry-run mock mode only."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

os.environ["KRILLINAI_DRY_RUN"] = "true"

from hf_client import HuggingFaceClient


def test_dry_run_health_check() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    hf = HuggingFaceClient()
    assert hf.check_health() is True


def test_dry_run_transcribe() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    hf = HuggingFaceClient()
    srt = hf.transcribe("dummy_audio.flac")
    assert "[Dry run] Transcribed subtitle" in srt


if __name__ == "__main__":
    test_dry_run_health_check()
    test_dry_run_transcribe()
    print("All HuggingFace client tests passed.")
