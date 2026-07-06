import json
from pathlib import Path
from config import load_config
from logger import get_logger

logger = get_logger("GoogleDriveClient")


class GoogleDriveClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def _credentials(self):
        from google.oauth2 import service_account

        raw = self.cfg.google_drive_credentials
        if not raw:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS is not configured")

        candidate = Path(raw)
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        if candidate.exists():
            return service_account.Credentials.from_service_account_file(str(candidate), scopes=scopes)
        return service_account.Credentials.from_service_account_info(json.loads(raw), scopes=scopes)

    def upload_file(self, local_path: str, mime_type: str = "video/mp4") -> str:
        """Upload to Google Drive and return the shareable link."""
        path = Path(local_path)
        file_size = path.stat().st_size
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path} ({file_size} bytes) to Google Drive")
            return "https://drive.google.com/file/d/DRY_RUN_PLACEHOLDER/view"

        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        metadata: dict[str, object] = {"name": path.name}
        if self.cfg.google_drive_folder_id:
            metadata["parents"] = [self.cfg.google_drive_folder_id]

        service = build("drive", "v3", credentials=self._credentials(), cache_discovery=False)
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)
        uploaded = service.files().create(
            body=metadata,
            media_body=media,
            fields="id,webViewLink",
        ).execute()

        file_id = uploaded["id"]
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
        details = service.files().get(fileId=file_id, fields="webViewLink").execute()
        return details.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
