from config import load_config
from logger import get_logger

logger = get_logger("GeminiClient")


class GeminiClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def translate_srt(self, srt_text: str, target_language: str = "vi") -> str:
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Translating SRT to {target_language}")
            return srt_text.replace("[Dry run]", "[Dry run translated]")

        if not self.cfg.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        # TODO: Implement Gemini translation API call using GEMINI_API_KEY and GEMINI_MODEL.
        raise NotImplementedError("Gemini translate placeholder")

    def synthesize_voice(self, text: str, voice: str = "") -> bytes:
        if self.cfg.dry_run:
            logger.info("[DRY RUN] Generating placeholder Gemini voice audio")
            return b"KRILLINAI_DRY_RUN_GEMINI_TTS"

        if not self.cfg.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        # TODO: Implement Gemini Voice TTS API call.
        raise NotImplementedError("Gemini Voice placeholder")
