#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gdrive_client import GoogleDriveClient


def test_upload_file_dry_run_returns_placeholder_link() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    path = Path("workdir/test-gdrive-video.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"video-bytes")

    link = GoogleDriveClient().upload_file(str(path))

    assert link == "https://drive.google.com/file/d/DRY_RUN_PLACEHOLDER/view"


if __name__ == "__main__":
    test_upload_file_dry_run_returns_placeholder_link()
    print("All Google Drive client tests passed.")
