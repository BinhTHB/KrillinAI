#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from models import JobStage, JobStatus
from r2_client import R2Client
from workflows.ingest import run


def reset_workdir(job_id: str) -> None:
    shutil.rmtree("workdir/mock-r2", ignore_errors=True)
    shutil.rmtree(Path("workdir") / job_id, ignore_errors=True)


def test_dry_run_ingest_workflow() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    job_id = "test-m3-job"
    reset_workdir(job_id)

    ret = run(job_id, "https://example.com/video.mp4", 123, 456)
    assert ret == 0

    mock_r2_dir = Path("workdir/mock-r2/jobs") / job_id
    assert (mock_r2_dir / "video_orig.mp4").exists()
    assert (mock_r2_dir / "audio_orig.flac").exists()
    assert (mock_r2_dir / "metadata.json").exists()

    metadata = json.loads((mock_r2_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["job_id"] == job_id
    assert metadata["status"] == JobStatus.INGESTED.value
    assert metadata["current_stage"] == JobStage.AI_PIPELINE.value


def test_ingest_workflow_idempotency() -> None:
    os.environ["KRILLINAI_DRY_RUN"] = "true"
    job_id = "test-m3-job"
    reset_workdir(job_id)

    mock_r2_dir = Path("workdir/mock-r2/jobs") / job_id
    mock_r2_dir.mkdir(parents=True, exist_ok=True)
    (mock_r2_dir / "video_orig.mp4").write_text("existing_video", encoding="utf-8")
    (mock_r2_dir / "audio_orig.flac").write_text("existing_audio", encoding="utf-8")

    ret = run(job_id, "https://example.com/video.mp4", 123, 456)
    assert ret == 0

    assert (mock_r2_dir / "video_orig.mp4").read_text(encoding="utf-8") == "existing_video"
    assert (mock_r2_dir / "audio_orig.flac").read_text(encoding="utf-8") == "existing_audio"


if __name__ == "__main__":
    test_dry_run_ingest_workflow()
    test_ingest_workflow_idempotency()
    print("All Ingest workflow tests passed.")
