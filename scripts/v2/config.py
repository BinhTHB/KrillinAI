# ==========================================================================
# KrillinAI v2 – Environment Configuration Loader
# ==========================================================================
# Loads settings from environment variables with fallback values.
# No real secrets are stored here.
# ==========================================================================

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    # Dry Run mode for testing infrastructure without API keys
    dry_run: bool

    # Cloudflare R2 Settings
    r2_access_key_id: Optional[str]
    r2_secret_access_key: Optional[str]
    r2_endpoint: Optional[str]
    r2_bucket: Optional[str]
    r2_region: str

    # Hugging Face Space Settings
    hf_space_url: Optional[str]
    whisper_model: str

    # Gemini Settings
    gemini_api_key: Optional[str]
    gemini_model: str

    # Telegram Settings
    telegram_bot_token: Optional[str]
    telegram_api_url: str

    # Google Drive Settings
    google_drive_credentials: Optional[str]  # Can be JSON string or path to JSON
    google_drive_folder_id: Optional[str]


def load_config() -> Config:
    dry_run = os.getenv("KRILLINAI_DRY_RUN", "false").lower() in ("true", "1", "yes")

    return Config(
        dry_run=dry_run,
        
        # Cloudflare R2
        r2_access_key_id=os.getenv("CF_R2_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=os.getenv("CF_R2_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_ACCESS_KEY"),
        r2_endpoint=os.getenv("CF_R2_ENDPOINT") or os.getenv("R2_ENDPOINT"),
        r2_bucket=os.getenv("CF_R2_BUCKET") or os.getenv("R2_BUCKET"),
        r2_region=os.getenv("CF_R2_REGION") or os.getenv("R2_REGION", "auto"),
        
        # Hugging Face
        hf_space_url=os.getenv("HF_SPACE_URL"),
        whisper_model=os.getenv("WHISPER_MODEL", "base"),
        
        # Gemini
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        
        # Telegram
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_api_url=os.getenv("TELEGRAM_API_URL", "https://api.telegram.org/bot"),
        
        # Google Drive
        google_drive_credentials=os.getenv("GOOGLE_DRIVE_CREDENTIALS"),
        google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
    )
