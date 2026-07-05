#!/usr/bin/env python3
"""Workflow #3 – Render Orchestration.

Download assets from R2, render final video with FFmpeg, upload final video,
and notify Telegram.
"""

import argparse
import sys
from pathlib import Path

# Ensure we can import modules from scripts/v2/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_config
from logger import get_logger
from models import JobStatus
from r2_client import R2Client
from telegram_client import TelegramClient
from gdrive_client import GoogleDriveClient
from layout import StorageLayout

logger = get_logger("RenderWorkflow")


def run(job_id: str, chat_id: int, message_id: int) -> int:
    cfg = load_config()
    logger.info(f"Starting render for job {job_id}")

    r2 = R2Client()
    metadata = r2.get_metadata(job_id)
    if not metadata:
        logger.error(f"Metadata not found for job {job_id}")
        return 1

    # Prepare local workdir
    workdir = Path("workdir") / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    # Local file paths
    video_path = workdir / "video_orig.mp4"
    subtitle_path = workdir / "translated_vi.srt"
    tts_audio_path = workdir / "tts_voice.wav"
    final_video_path = workdir / "video_final.mp4"

    # Download required assets
    metadata.status = JobStatus.RENDERING
    r2.save_metadata(metadata)
    r2.download_file(StorageLayout.get_video_orig_key(job_id), str(video_path))
    r2.download_file(StorageLayout.get_translated_srt_key(job_id), str(subtitle_path))
    r2.download_file(StorageLayout.get_tts_audio_key(job_id), str(tts_audio_path))

    # Render video
    if cfg.dry_run:
        final_video_path.write_bytes(b"KRILLINAI_DRY_RUN_FINAL_VIDEO")
        logger.info(f"[DRY RUN] Created placeholder final video: {final_video_path}")
    else:
        # TODO: Implement FFmpeg render:
        # 1. Detect original subtitle area.
        # 2. Apply blur filter to original subtitle region.
        # 3. Overlay translated subtitles.
        # 4. Replace/mix audio with TTS audio.
        # 5. Encode H.264/AAC final MP4.
        raise NotImplementedError("Real FFmpeg rendering not implemented")

    # Upload final video to R2
    r2.upload_file(str(final_video_path), StorageLayout.get_video_final_key(job_id))

    # Upload result to Telegram or Google Drive
    metadata.status = JobStatus.UPLOADING
    r2.save_metadata(metadata)
    tg = TelegramClient()
    if final_video_path.stat().st_size <= 50 * 1024 * 1024:
        tg.send_video(chat_id, str(final_video_path), caption=f"KrillinAI job {job_id} completed")
    else:
        drive = GoogleDriveClient()
        link = drive.upload_file(str(final_video_path))
        tg.send_message(chat_id, f"✅ Video đã render xong: {link}")

    metadata.status = JobStatus.COMPLETED
    r2.save_metadata(metadata)
    tg.send_message(chat_id, f"🎉 <b>Hoàn tất!</b> Job <code>{job_id}</code> đã xử lý xong.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render workflow orchestrator")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--message-id", type=int, required=True)
    args = parser.parse_args()

    return run(args.job_id, args.chat_id, args.message_id)


if __name__ == "__main__":
    sys.exit(main())
