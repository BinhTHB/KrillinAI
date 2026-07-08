#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from telegram_client import TelegramClient, _build_multipart_form_data


def test_build_multipart_form_data_includes_video_file() -> None:
    path = Path("workdir/test-telegram-video.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"video-bytes")

    body, boundary = _build_multipart_form_data({"chat_id": "123"}, {"video": str(path)})

    assert boundary.encode("utf-8") in body
    assert b'name="chat_id"' in body
    assert b'name="video"; filename="test-telegram-video.mp4"' in body
    assert b"video-bytes" in body


def test_send_video_dry_run_accepts_existing_file() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    path = Path("workdir/test-telegram-video.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"video-bytes")

    TelegramClient().send_video(123, str(path), "caption")


if __name__ == "__main__":
    test_build_multipart_form_data_includes_video_file()
    test_send_video_dry_run_accepts_existing_file()
    print("All Telegram client tests passed.")
