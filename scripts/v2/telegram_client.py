import json
import urllib.request

from config import load_config
from logger import get_logger

logger = get_logger("TelegramClient")


class TelegramClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def send_message(self, chat_id: int | str, text: str, parse_mode: str = "HTML") -> None:
        if self.cfg.dry_run or not self.cfg.telegram_bot_token:
            logger.info(f"[DRY RUN] Telegram message to {chat_id}: {text}")
            return

        payload = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode("utf-8")
        endpoint = f"{self.cfg.telegram_api_url}{self.cfg.telegram_bot_token}/sendMessage"
        req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            logger.info(resp.read().decode("utf-8"))

    def send_video(self, chat_id: int | str, video_path: str, caption: str = "") -> None:
        if self.cfg.dry_run or not self.cfg.telegram_bot_token:
            logger.info(f"[DRY RUN] Would upload video {video_path} to Telegram chat {chat_id}")
            return

        # TODO: Implement multipart/form-data Telegram sendVideo API call.
        raise NotImplementedError("Telegram send_video placeholder")
