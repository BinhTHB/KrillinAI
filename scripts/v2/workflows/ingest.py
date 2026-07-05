#!/usr/bin/env python3
"""Workflow #1 – Ingest Orchestration.

Download video, extract audio, convert to FLAC, upload all assets to R2,
save metadata, notify Telegram, and output job_id for next workflow.
"""

import argparse
import shutil
import subprocess
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

    r2 = R2Client()
    video_key = StorageLayout.get_video_orig_key(job_id)
    audio_key = StorageLayout.get_audio_orig_key(job_id)

    # Idempotency: Skip download/extract if files already exist on R2
    # TODO: Integrate queue state recovery check if necessary
    try:
        if r2.exists(video_key) and r2.exists(audio_key):
            logger.info("Original video and audio already exist in storage, skipping ingest steps")
            tg = TelegramClient()
            tg.send_message(chat_id, f"🔄 <b>[Workflow #1]</b> Dữ liệu gốc đã tồn tại cho job <code>{job_id}</code>. Đang bỏ qua bước ingest...")
            
            # Make sure metadata is saved as ready
            metadata = JobMetadata.new(job_id, video_url, chat_id, message_id)
            metadata.status = JobStatus.INGESTED
            metadata.current_stage = JobStage.AI_PIPELINE
            r2.save_metadata(metadata)
            
            print(f"job_id={job_id}")
            return 0
    except NotImplementedError:
        # Fallback if S3 check is not configured/implemented
        logger.info("Idempotency exists check not available, proceeding with ingest")

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
        if not shutil.which("yt-dlp"):
            raise RuntimeError("yt-dlp is required but not installed or not on PATH")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg is required but not installed or not on PATH")

        logger.info(f"Downloading video from {video_url} with yt-dlp")
        subprocess.run(
            [
                "yt-dlp",
                "-f",
                "mp4/best",
                "-o",
                str(video_path),
                video_url,
            ],
            check=True,
        )

        logger.info("Extracting FLAC audio with ffmpeg")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "flac",
                "-compression_level",
                "12",
                str(audio_path),
            ],
            check=True,
        )

    # Upload to R2
    r2.upload_file(str(video_path), video_key)
    r2.upload_file(str(audio_path), audio_key)

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
