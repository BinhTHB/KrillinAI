#!/usr/bin/env python3
"""Workflow #1 – Ingest Orchestration.

Download video, extract audio, convert to FLAC, upload all assets to R2,
save metadata, notify Telegram, and output job_id for next workflow.
"""

import argparse
import sys
from pathlib import Path

# Ensure we can import modules from scripts/v2/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_config
from logger import get_logger
from models import JobMetadata, JobStatus, JobStage
from r2_client import R2Client
from telegram_client import TelegramClient
from layout import StorageLayout

logger = get_logger("IngestWorkflow")


def run(job_id: str, video_url: str, chat_id: int, message_id: int) -> int:
    cfg = load_config()
    logger.info(f"Starting ingest for job {job_id}")

    # Prepare local workdir
    workdir = Path("workdir") / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    # Local file paths
    video_path = workdir / "video_orig.mp4"
    audio_path = workdir / "audio_orig.flac"

    if cfg.dry_run:
        # Placeholder files
        video_path.write_bytes(b"KRILLINAI_DRY_RUN_VIDEO")
        audio_path.write_bytes(b"KRILLINAI_DRY_RUN_AUDIO")
        logger.info(f"[DRY RUN] Created placeholder video/audio in {workdir}")
    else:
        # TODO: Implement real video download (yt-dlp) and audio extraction (ffmpeg)
        raise NotImplementedError("Real video download + audio extraction not implemented")

    # Upload to R2
    r2 = R2Client()
    r2.upload_file(str(video_path), StorageLayout.get_video_orig_key(job_id))
    r2.upload_file(str(audio_path), StorageLayout.get_audio_orig_key(job_id))

    # Save metadata
    metadata = JobMetadata.new(job_id, video_url, chat_id, message_id)
    metadata.status = JobStatus.INGESTED
    metadata.current_stage = JobStage.AI_PIPELINE
    r2.save_metadata(metadata)

    # Notify user
    tg = TelegramClient()
    tg.send_message(chat_id, f"✅ <b>[Workflow #1]</b> Ingest hoàn tất. Chuyển giao sang AI Pipeline (job: <code>{job_id}</code>).")

    # Output job_id for next workflow (captured by GitHub Actions)
    print(f"job_id={job_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest workflow orchestrator")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--message-id", type=int, required=True)
    args = parser.parse_args()

    return run(args.job_id, args.video_url, args.chat_id, args.message_id)


if __name__ == "__main__":
    sys.exit(main())
