#!/usr/bin/env python3
"""Workflow #2 – AI Pipeline Orchestration.

Check HF space health, download audio from R2, run Whisper transcription,
align SRT timestamps, translate using Gemini, synthesize voice audio,
upload all results to R2, and update job metadata.
"""

import argparse
import sys
from pathlib import Path

# Ensure we can import modules from scripts/v2/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logger import get_logger
from models import JobStatus, JobStage
from r2_client import R2Client
from telegram_client import TelegramClient
from hf_client import HuggingFaceClient
from gemini_client import GeminiClient
from layout import StorageLayout

logger = get_logger("AIPipelineWorkflow")


def run(job_id: str, chat_id: int, message_id: int) -> int:
    logger.info(f"Starting AI Pipeline for job {job_id}")

    r2 = R2Client()
    metadata = r2.get_metadata(job_id)
    if not metadata:
        logger.error(f"Metadata not found for job {job_id}")
        return 1

    # Keys
    audio_key = StorageLayout.get_audio_orig_key(job_id)
    raw_srt_key = StorageLayout.get_raw_srt_key(job_id)
    aligned_srt_key = StorageLayout.get_aligned_srt_key(job_id)
    translated_srt_key = StorageLayout.get_translated_srt_key(job_id)
    tts_audio_key = StorageLayout.get_tts_audio_key(job_id)

    # Local workdir
    workdir = Path("workdir") / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    audio_path = workdir / "audio_orig.flac"
    raw_srt_path = workdir / "raw_whisper.srt"
    aligned_srt_path = workdir / "aligned.srt"
    translated_srt_path = workdir / "translated_vi.srt"
    tts_audio_path = workdir / "tts_voice.wav"

    # Step 1: Transcribe
    if r2.exists(raw_srt_key):
        logger.info("Raw SRT already exists in R2, skipping transcription")
        r2.download_file(raw_srt_key, str(raw_srt_path))
    else:
        metadata.status = JobStatus.TRANSCRIBING
        metadata.current_stage = JobStage.AI_PIPELINE
        r2.save_metadata(metadata)
        r2.download_file(audio_key, str(audio_path))
        hf = HuggingFaceClient()
        if not hf.check_health():
            logger.error("Hugging Face Space is not healthy")
            return 1
        raw_srt = hf.transcribe(str(audio_path))
        raw_srt_path.write_text(raw_srt, encoding="utf-8")
        r2.upload_file(str(raw_srt_path), raw_srt_key)

    # Step 2: Anchor Alignment
    if r2.exists(aligned_srt_key):
        logger.info("Aligned SRT already exists in R2, skipping alignment")
        r2.download_file(aligned_srt_key, str(aligned_srt_path))
    else:
        metadata.status = JobStatus.ALIGNING
        r2.save_metadata(metadata)
        if not raw_srt_path.exists():
            r2.download_file(raw_srt_key, str(raw_srt_path))
        # TODO: port align_srt_to_speech.py logic or call it as subprocess.
        aligned_srt_path.write_text(raw_srt_path.read_text(encoding="utf-8"), encoding="utf-8")
        r2.upload_file(str(aligned_srt_path), aligned_srt_key)

    # Step 3: Gemini Translation
    if r2.exists(translated_srt_key):
        logger.info("Translated SRT already exists in R2, skipping translation")
        r2.download_file(translated_srt_key, str(translated_srt_path))
    else:
        metadata.status = JobStatus.TRANSLATING
        r2.save_metadata(metadata)
        if not aligned_srt_path.exists():
            r2.download_file(aligned_srt_key, str(aligned_srt_path))
        gemini = GeminiClient()
        translated_srt = gemini.translate_srt(aligned_srt_path.read_text(encoding="utf-8"), "vi")
        translated_srt_path.write_text(translated_srt, encoding="utf-8")
        r2.upload_file(str(translated_srt_path), translated_srt_key)

    # Step 4: TTS (Skip monolithic TTS generation to avoid API quota errors; render pipeline will generate aligned TTS)

    # Save final stage metadata
    metadata.current_stage = JobStage.RENDER
    metadata.status = JobStatus.TTS_READY
    r2.save_metadata(metadata)

    # Notify user
    tg = TelegramClient()
    tg.send_message(chat_id, f"✅ <b>[Workflow #2]</b> AI Pipeline hoàn tất. Bắt đầu Render (job: <code>{job_id}</code>).")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Pipeline workflow orchestrator")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--message-id", type=int, required=True)
    args = parser.parse_args()

    return run(args.job_id, args.chat_id, args.message_id)


if __name__ == "__main__":
    sys.exit(main())
