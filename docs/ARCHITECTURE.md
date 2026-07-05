# KrillinAI v2 Architecture

KrillinAI v2 keeps the current serverless event-driven pipeline from `architecture.md`.

## Pipeline

1. Telegram sends a video URL to Cloudflare Worker.
2. Cloudflare Worker validates the request and dispatches GitHub event `telegram_video_ingest`.
3. Workflow #1 `ingest.yml` runs `scripts/v2/workflows/ingest.py`.
4. Workflow #1 dispatches event `ai_pipeline_start`.
5. Workflow #2 `ai_pipeline.yml` runs `scripts/v2/workflows/ai_pipeline.py`.
6. Workflow #2 dispatches event `render_start`.
7. Workflow #3 `render.yml` runs `scripts/v2/workflows/render.py`.
8. Final video is uploaded to Telegram or Google Drive depending on size.

No workflow uses `workflow_run`. Workflow chaining is explicit via `repository_dispatch`.

## Shared modules

- `scripts/v2/r2_client.py`: Cloudflare R2 placeholder client.
- `scripts/v2/telegram_client.py`: Telegram placeholder client.
- `scripts/v2/github_client.py`: GitHub dispatch placeholder client.
- `scripts/v2/hf_client.py`: Hugging Face ASR placeholder client.
- `scripts/v2/gemini_client.py`: Gemini translation/TTS placeholder client.
- `scripts/v2/gdrive_client.py`: Google Drive upload placeholder client.
- `scripts/v2/layout.py`: canonical R2 layout.
- `scripts/v2/models.py`: job metadata, status, and stage models.
- `scripts/v2/retry.py`: shared retry helper.
- `scripts/v2/logger.py`: shared logger.

## R2 layout

All pipeline assets are stored under `jobs/{job_id}/`:

```text
jobs/{job_id}/metadata.json
jobs/{job_id}/video_orig.mp4
jobs/{job_id}/audio_orig.flac
jobs/{job_id}/raw_whisper.srt
jobs/{job_id}/aligned.srt
jobs/{job_id}/translated_vi.srt
jobs/{job_id}/tts_voice.wav
jobs/{job_id}/video_final.mp4
```

## Idempotency

Each workflow checks whether its expected R2 output already exists before doing work.

- Ingest skips video/audio processing when original assets exist.
- AI Pipeline skips transcription, alignment, translation, and TTS independently when their outputs exist.
- Render skips FFmpeg rendering when the final video exists.

## Branch strategy

- `master`: development / upstream sync.
- `working-branch`: production.

## TODO

- Implement real R2 upload/download and `head_object` exists checks.
- Implement HF Space `/transcribe` multipart call.
- Implement Gemini translation and TTS.
- Implement FFmpeg render pipeline.
- Implement Telegram video upload.
- Implement Google Drive upload.
- Future enhancement: add Cloudflare Queue for load control and retries.
