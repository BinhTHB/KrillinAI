import json
import os
import shutil
from pathlib import Path
from typing import Optional

from config import load_config
from logger import get_logger
from models import JobMetadata

logger = get_logger("R2Client")


class R2Client:
    def __init__(self) -> None:
        self.cfg = load_config()
        # Dry-run mock storage root
        self.mock_root = Path("workdir/mock-r2")
        if self.cfg.dry_run:
            self.mock_root.mkdir(parents=True, exist_ok=True)

    def _mock_path(self, key: str) -> Path:
        """Return the mock filesystem path for a given R2 key (dry-run only)."""
        return self.mock_root / key

    def exists(self, key: str) -> bool:
        """Check if an object exists in R2 (dry-run mock or real S3 HEAD)."""
        if self.cfg.dry_run:
            return self._mock_path(key).exists()

        # TODO: implement real S3 HEAD request via boto3
        # s3 = boto3.client(...)
        # try:
        #     s3.head_object(Bucket=self.cfg.r2_bucket, Key=key)
        #     return True
        # except s3.exceptions.ClientError:
        #     return False
        raise NotImplementedError("R2 exists check placeholder — implement boto3 head_object")

    def upload_file(self, local_path: str, key: str) -> None:
        """Upload a file to R2; in dry-run also mirror to mock storage for idempotency."""
        if self.cfg.dry_run:
            mock = self._mock_path(key)
            mock.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, mock)
            logger.info(f"[DRY RUN] Uploaded {local_path} -> mock R2:{key}")
            return

        # TODO: integrate boto3 S3 upload
        # s3.upload_file(local_path, self.cfg.r2_bucket, key)
        raise NotImplementedError("R2 upload placeholder — set up CF_R2_* secrets and implement boto3 client")

    def download_file(self, key: str, local_path: str) -> None:
        """Download a file from R2; in dry-run read from mock storage if present."""
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if self.cfg.dry_run:
            mock = self._mock_path(key)
            if mock.exists():
                shutil.copy2(mock, local_path)
                logger.info(f"[DRY RUN] Downloaded mock R2:{key} -> {local_path}")
                return
            # If mock does not exist, create a placeholder
            Path(local_path).write_text(f"placeholder content for R2:{key}\n", encoding="utf-8")
            logger.info(f"[DRY RUN] Created placeholder for missing mock R2:{key}")
            return

        # TODO: integrate boto3 S3 download
        # s3.download_file(self.cfg.r2_bucket, key, local_path)
        raise NotImplementedError("R2 download placeholder — set up CF_R2_* secrets and implement boto3 client")

    def get_metadata(self, job_id: str) -> Optional[JobMetadata]:
        key = f"jobs/{job_id}/metadata.json"
        local_tmp = f"workdir/tmp_{job_id}_metadata.json"
        try:
            self.download_file(key, local_tmp)
            if not os.path.exists(local_tmp):
                return None
            with open(local_tmp, encoding="utf-8") as f:
                data = json.load(f)
            return JobMetadata(**data)
        except NotImplementedError:
            logger.info(f"Stubbing metadata load for job {job_id}")
            return JobMetadata.new(job_id, "https://example.com/video.mp4", 0, 0)
        finally:
            if os.path.exists(local_tmp):
                os.unlink(local_tmp)

    def save_metadata(self, metadata: JobMetadata) -> None:
        r2_path = metadata.get_r2_path()
        local_tmp = f"workdir/tmp_{metadata.job_id}_metadata.json"
        os.makedirs("workdir", exist_ok=True)
        with open(local_tmp, "w", encoding="utf-8") as f:
            json.dump(metadata.__dict__, f, ensure_ascii=False, indent=2)
        try:
            self.upload_file(local_tmp, r2_path)
        finally:
            if os.path.exists(local_tmp):
                os.unlink(local_tmp)
