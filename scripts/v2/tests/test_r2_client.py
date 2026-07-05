#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from models import JobMetadata
from r2_client import R2Client


def reset_mock_root() -> None:
    shutil.rmtree("workdir/mock-r2", ignore_errors=True)


def test_exists_returns_false_for_missing_key() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    reset_mock_root()
    client = R2Client()
    assert client.exists("jobs/test-r2/missing.txt") is False


def test_upload_and_download_roundtrip() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    reset_mock_root()
    client = R2Client()
    source = Path("workdir/test-r2-source.txt")
    target = Path("workdir/test-r2-target.txt")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("hello r2\n", encoding="utf-8")

    client.upload_file(str(source), "jobs/test-r2/file.txt")
    assert client.exists("jobs/test-r2/file.txt") is True
    client.download_file("jobs/test-r2/file.txt", str(target))
    assert target.read_text(encoding="utf-8") == "hello r2\n"


def test_metadata_save_and_load() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    reset_mock_root()
    client = R2Client()
    metadata = JobMetadata.new("test-r2", "https://example.com/video.mp4", 123, 456)

    client.save_metadata(metadata)
    loaded = client.get_metadata("test-r2")

    assert loaded is not None
    assert loaded.job_id == "test-r2"
    assert loaded.video_url == "https://example.com/video.mp4"
    assert loaded.chat_id == 123
    assert loaded.message_id == 456


if __name__ == "__main__":
    test_exists_returns_false_for_missing_key()
    test_upload_and_download_roundtrip()
    test_metadata_save_and_load()
    print("All tests passed.")
