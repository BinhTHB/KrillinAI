import json
import os
from pathlib import Path
from typing import Optional

from config import load_config
from logger import get_logger
from models import JobMetadata

logger = get_logger("R2Client")


class R2Client:
    def __init__(self) -> None:
        self.cfg = load_config()

    def upload_file(self, local_path: str, key: str) -> None:
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path} -> R2:{key}")
            return

        # TODO: integrate boto3 S3 client; credentials are loaded from CF_R2_* env vars via config.py
        # s3.upload_file(local_path, self.cfg.r2_bucket, key)
        raise NotImplementedError("R2 upload placeholder — set up CF_R2_* secrets and implement boto3 client")

    def download_file(self, key: str, local_path: str) -> None:
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Would download R2:{key} -> {local_path}")
            Path(local_path).write_text(f"placeholder content for R2:{key}\n", encoding="utf-8")
            return

        # TODO: integrate boto3 S3 client; credentials are loaded from CF_R2_* env vars via config.py
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

