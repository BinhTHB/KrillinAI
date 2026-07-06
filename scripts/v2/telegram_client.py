import json
import mimetypes
import uuid
import urllib.request
from pathlib import Path

from config import load_config
from logger import get_logger

logger = get_logger("TelegramClient")

def _build_multipart_form_data(fields: dict[str, str], files: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"----KrillinAI{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
            str(value).encode("utf-8"),
            b"\r\n",
        ])

    for name, file_path in files.items():
        path = Path(file_path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            path.read_bytes(),
            b"\r\n",
        ])

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


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
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Telegram video not found: {video_path}")

        if self.cfg.dry_run or not self.cfg.telegram_bot_token:
            logger.info(f"[DRY RUN] Would upload video {video_path} to Telegram chat {chat_id}")
            return

        fields = {"chat_id": str(chat_id)}
        if caption:
            fields["caption"] = caption
            fields["parse_mode"] = "HTML"
        body, boundary = _build_multipart_form_data(fields, {"video": video_path})
        endpoint = f"{self.cfg.telegram_api_url}{self.cfg.telegram_bot_token}/sendVideo"
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            logger.info(resp.read().decode("utf-8"))
