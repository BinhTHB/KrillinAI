#!/usr/bin/env python3
"""Workflow #1 – Ingest Orchestration.

Download video, extract audio, convert to FLAC, upload all assets to R2,
save metadata, notify Telegram, and output job_id for next workflow.
"""

import argparse
import os
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

def _is_douyin_url(video_url: str) -> bool:
    lower_url = video_url.lower()
    return "douyin.com" in lower_url or "iesdouyin.com" in lower_url

def _resolve_cookies_file(workdir: Path) -> Path | None:
    env_cookies = os.environ.get("YT_DLP_COOKIES", "").strip()
    if env_cookies:
        cookies_path = workdir / "cookies.txt"
        cookies_path.write_text(env_cookies + "\n", encoding="utf-8")
        logger.info("Using yt-dlp cookies from YT_DLP_COOKIES")
        return cookies_path

    local_cookies = Path("cookies.txt")
    if local_cookies.exists():
        logger.info("Using local cookies.txt for yt-dlp")
        return local_cookies

    return None

def _cookies_file_to_header(cookies_path: Path) -> str:
    cookies = []
    for line in cookies_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7 and parts[5]:
            cookies.append(f"{parts[5]}={parts[6]}")
    return "; ".join(cookies)

def _download_with_f2(video_url: str, workdir: Path, video_path: Path, cookies_path: Path | None) -> bool:
    if not shutil.which("f2"):
        logger.info("f2 is not installed; skipping Douyin fallback")
        return False

    f2_cmd = [
        "f2",
        "dy",
        "-M",
        "one",
        "-u",
        video_url,
        "-p",
        str(workdir),
        "-l",
        "en_US",
    ]
    if cookies_path:
        cookie_header = _cookies_file_to_header(cookies_path)
        if cookie_header:
            f2_cmd.extend(["-k", cookie_header])

    logger.info("Trying f2 fallback for Douyin download")
    result = subprocess.run(
        f2_cmd,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        logger.info(f"f2 returned non-zero status; checking downloaded files anyway: {result.stderr[:300]}")

    downloaded_files = [
        path
        for path in workdir.rglob("*.mp4")
        if path.resolve() != video_path.resolve() and path.stat().st_size > 0
    ]
    if not downloaded_files:
        logger.error(f"f2 fallback did not produce an mp4 file. stderr: {result.stderr[:500]}")
        return False

    downloaded = max(downloaded_files, key=lambda path: path.stat().st_size)
    if video_path.exists():
        video_path.unlink()
    shutil.move(str(downloaded), str(video_path))
    logger.info(f"f2 fallback downloaded video to {video_path}")
    return True


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

        cookies_path = _resolve_cookies_file(workdir)
        yt_dlp_cmd = [
            "yt-dlp",
            "-f",
            "mp4/best",
            "-o",
            str(video_path),
        ]
        if cookies_path:
            yt_dlp_cmd.extend(["--cookies", str(cookies_path)])
        yt_dlp_cmd.append(video_url)

        logger.info(f"Downloading video from {video_url} with yt-dlp")
        try:
            subprocess.run(
                yt_dlp_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp failed: {e.stderr}")
            if _is_douyin_url(video_url) and _download_with_f2(video_url, workdir, video_path, cookies_path):
                logger.info("Recovered from yt-dlp failure using f2 fallback")
            else:
                tg = TelegramClient()
                error_msg = f"❌ <b>[Workflow #1]</b> Tải video thất bại (yt-dlp error).\n\n"
                if "cookies" in e.stderr.lower() or "cookie" in e.stderr.lower():
                    error_msg += "Nguồn video này (Douyin/TikTok) yêu cầu cookies để tải. Vui lòng cập nhật cookies mới rồi thử lại."
                else:
                    error_msg += f"Chi tiết: <code>{e.stderr[:200]}...</code>"
                tg.send_message(chat_id, error_msg)
                metadata = JobMetadata.new(job_id, video_url, chat_id, message_id)
                metadata.status = JobStatus.FAILED
                metadata.current_stage = JobStage.INGEST
                r2.save_metadata(metadata)
                raise e

        logger.info("Extracting FLAC audio with ffmpeg")
        try:
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
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            tg = TelegramClient()
            tg.send_message(chat_id, f"❌ <b>[Workflow #1]</b> Trích xuất âm thanh thất bại (FFmpeg error).\n\nChi tiết: <code>{e.stderr[:200]}...</code>")
            metadata = JobMetadata.new(job_id, video_url, chat_id, message_id)
            metadata.status = JobStatus.FAILED
            metadata.current_stage = JobStage.INGEST
            r2.save_metadata(metadata)
            raise e

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
