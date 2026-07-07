#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from layout import StorageLayout
from models import JobStatus, JobStage
from r2_client import R2Client
from telegram_client import TelegramClient
from logger import get_logger

logger = get_logger("GoPipelineIO")

def download_video(job_id: str, output_path: str):
    r2 = R2Client()
    metadata = r2.get_metadata(job_id)
    if metadata:
        metadata.status = JobStatus.TRANSCRIBING
        metadata.current_stage = JobStage.AI_PIPELINE
        r2.save_metadata(metadata)
    video_key = StorageLayout.get_video_orig_key(job_id)
    logger.info(f"Downloading R2:{video_key} -> {output_path}")
    r2.download_file(video_key, output_path)

def upload_notify(job_id: str, chat_id: int, input_path: str):
    r2 = R2Client()
    tg = TelegramClient()
    metadata = r2.get_metadata(job_id)
    if metadata:
        metadata.status = JobStatus.UPLOADING
        metadata.current_stage = JobStage.RENDER
        r2.save_metadata(metadata)
    final_key = StorageLayout.get_video_final_key(job_id)
    logger.info(f"Uploading {input_path} -> R2:{final_key}")
    r2.upload_file(input_path, final_key)
    size = Path(input_path).stat().st_size
    if size <= 50 * 1024 * 1024:
        tg.send_video(chat_id, input_path, caption=f"KrillinAI job {job_id} completed")
    else:
        link = r2.generate_presigned_url(final_key)
        tg.send_message(chat_id, f"Video hoan tat! Link tai het han sau 24 gio: {link}")
    tg.send_message(chat_id, f"Hoan tat! Job {job_id} da xu ly xong toan bo pipeline.")
    if metadata:
        metadata.status = JobStatus.COMPLETED
        r2.save_metadata(metadata)

def handle_error(job_id: str, chat_id: int, error_msg: str):
    r2 = R2Client()
    tg = TelegramClient()
    metadata = r2.get_metadata(job_id)
    if metadata:
        metadata.status = JobStatus.FAILED
        metadata.error_message = error_msg
        r2.save_metadata(metadata)
    tg.send_message(chat_id, f"That bai! Job {job_id} gap loi: {error_msg}")

def main():
    parser = argparse.ArgumentParser(description="Go Pipeline I/O Helper")
    parser.add_argument("command", choices=["download", "upload-notify", "error"])
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--chat-id", type=int)
    parser.add_argument("--path")
    parser.add_argument("--error-msg")
    args = parser.parse_args()
    if args.command == "download":
        if not args.path:
            logger.error("Download requires --path"); sys.exit(1)
        download_video(args.job_id, args.path)
    elif args.command == "upload-notify":
        if not args.path or not args.chat_id:
            logger.error("Upload-notify requires --path and --chat-id"); sys.exit(1)
        upload_notify(args.job_id, args.chat_id, args.path)
    elif args.command == "error":
        if not args.chat_id or not args.error_msg:
            logger.error("Error requires --chat-id and --error-msg"); sys.exit(1)
        handle_error(args.job_id, args.chat_id, args.error_msg)

if __name__ == "__main__":
    main()
