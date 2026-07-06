#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from layout import StorageLayout
from models import JobMetadata
from r2_client import R2Client
from workflows.render import run


def reset_workdir(job_id: str) -> None:
    shutil.rmtree("workdir/mock-r2", ignore_errors=True)
    shutil.rmtree(Path("workdir") / job_id, ignore_errors=True)


def test_dry_run_render_workflow_uploads_final_video() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    job_id = "test-render-job"
    reset_workdir(job_id)

    client = R2Client()
    metadata = JobMetadata.new(job_id, "https://example.com/video.mp4", 123, 456)
    client.save_metadata(metadata)

    source = Path("workdir") / job_id / "video_orig.mp4"
    subtitle = Path("workdir") / job_id / "translated_vi.srt"
    audio = Path("workdir") / job_id / "tts_voice.wav"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"placeholder video")
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nXin chao\n", encoding="utf-8")
    audio.write_bytes(b"placeholder audio")
    client.upload_file(str(source), StorageLayout.get_video_orig_key(job_id))
    client.upload_file(str(subtitle), StorageLayout.get_translated_srt_key(job_id))
    client.upload_file(str(audio), StorageLayout.get_tts_audio_key(job_id))

    assert run(job_id, 123, 456) == 0
    assert client.exists(StorageLayout.get_video_final_key(job_id))


if __name__ == "__main__":
    test_dry_run_render_workflow_uploads_final_video()
    print("All render workflow tests passed.")
