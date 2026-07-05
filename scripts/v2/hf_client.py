import requests
from config import load_config
from logger import get_logger

logger = get_logger("HuggingFaceClient")


class HuggingFaceClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def check_health(self) -> bool:
        if self.cfg.dry_run:
            logger.info("[DRY RUN] Hugging Face Space health check is always successful")
            return True

        if not self.cfg.hf_space_url:
            raise ValueError("HF_SPACE_URL is not configured")

        url = self.cfg.hf_space_url.rstrip("/") + "/health"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status") == "ready"
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
        return False

    def transcribe(self, audio_path: str, language: str = "") -> str:
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Transcribing {audio_path} via HF Space...")
            return "1\n00:00:00,000 --> 00:00:01,000\n[Dry run] Transcribed subtitle\n"

        if not self.cfg.hf_space_url:
            raise ValueError("HF_SPACE_URL is not configured")

        # TODO: Implement multipart/form-data upload to HF Space /transcribe endpoint.
        raise NotImplementedError("HuggingFace transcription: implement POST to HF Space")
