from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    INGESTED = "ingested"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    ALIGNING = "aligning"
    ALIGNED = "aligned"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    TTS_PROCESSING = "tts_processing"
    TTS_READY = "tts_ready"
    RENDERING = "rendering"
    RENDERED = "rendered"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(str, Enum):
    INGEST = "ingest"
    AI_PIPELINE = "ai_pipeline"
    RENDER = "render"


@dataclass
class JobMetadata:
    job_id: str
    video_url: str
    chat_id: int
    message_id: int
    status: JobStatus = JobStatus.PENDING
    current_stage: JobStage = JobStage.INGEST
    r2_prefix: str = ""
    created_at: str = ""
    updated_at: str = ""
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def get_r2_path(self) -> str:
        return f"{self.r2_prefix}/metadata.json"

    @classmethod
    def new(cls, job_id: str, video_url: str, chat_id: int, message_id: int) -> "JobMetadata":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            job_id=job_id,
            video_url=video_url,
            chat_id=chat_id,
            message_id=message_id,
            status=JobStatus.INGESTING,
            current_stage=JobStage.INGEST,
            r2_prefix=f"jobs/{job_id}",
            created_at=now,
            updated_at=now,
        )
