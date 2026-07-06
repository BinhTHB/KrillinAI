#!/usr/bin/env python3
"""Workflow #3 – Render Orchestration.

Download assets from R2, render final video with FFmpeg, upload final video,
and notify Telegram.
"""

import argparse
import sys
import shutil
from pathlib import Path

# Ensure we can import modules from scripts/v2/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logger import get_logger
from models import JobStatus
from r2_client import R2Client
from telegram_client import TelegramClient
from layout import StorageLayout
from render_ffmpeg import render_video

logger = get_logger("RenderWorkflow")


def run(job_id: str, chat_id: int, message_id: int) -> int:
    logger.info(f"Starting render for job {job_id}")

    r2 = R2Client()
    metadata = r2.get_metadata(job_id)
    if not metadata:
        logger.error(f"Metadata not found for job {job_id}")
        return 1

    final_key = StorageLayout.get_video_final_key(job_id)

    # Check if final video already exists (render may have been done)
    try:
        if r2.exists(final_key):
            logger.info("Final video already exists in R2, skipping render and uploading result directly")
            # Upload result to Telegram or an R2 presigned URL
            tg = TelegramClient()
            local = Path("workdir") / job_id / "video_final.mp4"
            local.parent.mkdir(parents=True, exist_ok=True)
            r2.download_file(final_key, str(local))
            send_result(tg, r2, chat_id, job_id, local)
            return 0
    except NotImplementedError:
        logger.info("R2 exists check not available, proceeding with render")

    # Prepare local workdir
    workdir = Path("workdir") / job_id
    workdir.mkdir(parents=True, exist_ok=True)

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

    if r2.exists(final_key):
        logger.info("Final video already uploaded, skipping render")
        r2.download_file(final_key, str(final_video_path))
    else:
        metadata.status = JobStatus.RENDERING
        r2.save_metadata(metadata)
        if r2.cfg.dry_run:
            logger.info("[DRY RUN] Skipping FFmpeg render and creating placeholder final video")
            shutil.copy2(video_path, final_video_path)
        else:
            render_video(video_path, subtitle_path, tts_audio_path, final_video_path)
        r2.upload_file(str(final_video_path), final_key)

    # Upload result to Telegram or an R2 presigned URL
    metadata.status = JobStatus.UPLOADING
    r2.save_metadata(metadata)
    send_result(TelegramClient(), r2, chat_id, job_id, final_video_path)

    metadata.status = JobStatus.COMPLETED
    r2.save_metadata(metadata)

    return 0


def send_result(tg: TelegramClient, r2: R2Client, chat_id: int, job_id: str, path: Path) -> None:
    """Upload final video (<50MB to Telegram, else R2 presigned URL) and notify user."""
    file_size = path.stat().st_size
    if file_size <= 50 * 1024 * 1024:
        tg.send_video(chat_id, str(path), caption=f"📺 KrillinAI job {job_id} completed")
    else:
        link = r2.generate_presigned_url(StorageLayout.get_video_final_key(job_id))
        tg.send_message(chat_id, f"📺 <b>Video hoàn tất!</b> File lớn hơn 50MB. Link tải hết hạn sau 24 giờ: {link}")

    tg.send_message(chat_id, f"🎉 <b>Hoàn tất!</b> Job <code>{job_id}</code> đã xử lý xong toàn bộ pipeline.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render workflow orchestrator")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--message-id", type=int, required=True)
    args = parser.parse_args()

    return run(args.job_id, args.chat_id, args.message_id)


if __name__ == "__main__":
    sys.exit(main())
