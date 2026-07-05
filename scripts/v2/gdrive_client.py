from pathlib import Path
from config import load_config
from logger import get_logger

logger = get_logger("GoogleDriveClient")


class GoogleDriveClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def upload_file(self, local_path: str, mime_type: str = "video/mp4") -> str:
        """Upload to Google Drive and return the shareable link."""
        file_size = Path(local_path).stat().st_size
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path} ({file_size} bytes) to Google Drive")
            return "https://drive.google.com/file/d/DRY_RUN_PLACEHOLDER/view"

        if not self.cfg.google_drive_credentials:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS is not configured")

        # TODO: Implement Google Drive API upload:
        # 1. Decode GOOGLE_DRIVE_CREDENTIALS from env (JSON string or path).
        # 2. Use google-auth + googleapiclient to upload file.
        # 3. Optionally set permissions to "anyone with link".
        # 4. Return the public link.
        raise NotImplementedError("Google Drive upload placeholder")
