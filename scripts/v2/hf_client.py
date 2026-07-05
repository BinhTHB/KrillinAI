import time
from pathlib import Path

import requests
from config import load_config
from logger import get_logger

logger = get_logger("HuggingFaceClient")


class HuggingFaceClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def check_health(self, timeout_seconds: int = 300, interval_seconds: int = 10) -> bool:
        if self.cfg.dry_run:
            logger.info("[DRY RUN] Hugging Face Space health check is always successful")
            return True

        if not self.cfg.hf_space_url:
            raise ValueError("HF_SPACE_URL is not configured")

        url = self.cfg.hf_space_url.rstrip("/") + "/health"
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ready":
                        return True
                    logger.info(f"HF Space status: {data.get('status', 'unknown')}")
                else:
                    logger.warning(f"HF Space health returned HTTP {resp.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Health check failed: {e}")
            time.sleep(interval_seconds)
        return False

    def transcribe(self, audio_path: str, language: str = "") -> str:
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Transcribing {audio_path} via HF Space...")
            return "1\n00:00:00,000 --> 00:00:01,000\n[Dry run] Transcribed subtitle\n"

        if not self.cfg.hf_space_url:
            raise ValueError("HF_SPACE_URL is not configured")

        if not self.check_health():
            raise RuntimeError("HF Space is not ready")

        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        url = self.cfg.hf_space_url.rstrip("/") + "/transcribe"
        data = {}
        if language:
            data["language"] = language

        with path.open("rb") as f:
            resp = requests.post(
                url,
                files={"file": (path.name, f, "application/octet-stream")},
                data=data,
                timeout=600,
            )
        resp.raise_for_status()
        return resp.text
