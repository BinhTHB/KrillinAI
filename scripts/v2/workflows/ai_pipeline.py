#!/usr/bin/env python3
"""Workflow #2 – AI Pipeline Orchestration.

Check HF space health, download audio from R2, run Whisper transcription,
align SRT timestamps, translate using Gemini, synthesize lồng tiếng audio,
upload all results to R2, and update job metadata.
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
from hf_client import HuggingFaceClient
from gemini_client import GeminiClient
from layout import StorageLayout

logger = get_logger("AIPipelineWorkflow")


def run(job_id: str, chat_id: int, message_id: int) -> int:
    cfg = load_config()
    logger.info(f"Starting AI Pipeline for job {job_id}")

    r2 = R2Client()
    metadata = r2.get_metadata(job_id)
    if not metadata:
        logger.error(f"Metadata not found for job {job_id}")
        return 1

    # Update metadata
    metadata.status = JobStatus.TRANSCRIBING
    metadata.current_stage = JobStage.AI_PIPELINE
    r2.save_metadata(metadata)

    # Prepare local workdir
    workdir = Path("workdir") / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    # Local file paths
    audio_path = workdir / "audio_orig.flac"
    raw_srt_path = workdir / "raw_whisper.srt"
    aligned_srt_path = workdir / "aligned.srt"
    translated_srt_path = workdir / "translated_vi.srt"
    tts_audio_path = workdir / "tts_voice.wav"

    # Download original audio
    r2.download_file(StorageLayout.get_audio_orig_key(job_id), str(audio_path))

    # Transcribe (Whisper)
    hf = HuggingFaceClient()
    if not hf.check_health():
        logger.error("Hugging Face Space is not healthy")
        return 1

    metadata.status = JobStatus.TRANSCRIBING
    r2.save_metadata(metadata)
    raw_srt = hf.transcribe(str(audio_path))
    raw_srt_path.write_text(raw_srt, encoding="utf-8")

    # Align timestamps
    metadata.status = JobStatus.ALIGNING
    r2.save_metadata(metadata)
    # TODO: port align_srt_to_speech.py logic or call it as subprocess
    # For skeleton, copy raw to aligned
    aligned_srt_path.write_text(raw_srt_path.read_text(encoding="utf-8"), encoding="utf-8")
    metadata.status = JobStatus.ALIGNED
    r2.save_metadata(metadata)

    # Translate (Gemini)
    metadata.status = JobStatus.TRANSLATING
    r2.save_metadata(metadata)
    gemini = GeminiClient()
    translated_srt = gemini.translate_srt(aligned_srt_path.read_text(encoding="utf-8"), "vi")
    translated_srt_path.write_text(translated_srt, encoding="utf-8")
    metadata.status = JobStatus.TRANSLATED
    r2.save_metadata(metadata)

    # Generate TTS voice (Gemini Voice / Edge-TTS)
    metadata.status = JobStatus.TTS_PROCESSING
    r2.save_metadata(metadata)
    tts_audio_data = gemini.synthesize_voice(translated_srt)
    tts_audio_path.write_bytes(tts_audio_data)
    metadata.status = JobStatus.TTS_READY
    r2.save_metadata(metadata)

    # Upload all AI assets to R2
    r2.upload_file(str(raw_srt_path), StorageLayout.get_raw_srt_key(job_id))
    r2.upload_file(str(aligned_srt_path), StorageLayout.get_aligned_srt_key(job_id))
    r2.upload_file(str(translated_srt_path), StorageLayout.get_translated_srt_key(job_id))
    r2.upload_file(str(tts_audio_path), StorageLayout.get_tts_audio_key(job_id))

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
