# KrillinAI v2 Architecture

KrillinAI v2 uses the current serverless event-driven pipeline from `architecture.md`. The architecture is unchanged: Telegram → Cloudflare Worker → GitHub Actions Workflows → Cloudflare R2 → Hugging Face/Gemini/FFmpeg → Telegram or Google Drive.

## Pipeline

1. Telegram sends a video URL to Cloudflare Worker.
2. Cloudflare Worker validates the request and dispatches GitHub event `telegram_video_ingest`.
3. Workflow #1 `ingest.yml` runs only `scripts/v2/workflows/ingest.py`.
4. Workflow #1 dispatches event `ai_pipeline_start`.
5. Workflow #2 `ai_pipeline.yml` runs only `scripts/v2/workflows/ai_pipeline.py`.
6. Workflow #2 dispatches event `render_start`.
7. Workflow #3 `render.yml` runs only `scripts/v2/workflows/render.py`.
8. Final video is uploaded to Telegram or Google Drive depending on size.

No workflow uses `workflow_run`. Workflow chaining is explicit via `repository_dispatch`.

## Shared modules

- `scripts/v2/r2_client.py`: Cloudflare R2 placeholder client with idempotency checks.
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

## Environment classification

- Secrets contain credentials only, e.g. R2 access keys, Telegram token, Gemini API key, Google Drive credentials.
- Variables contain non-sensitive runtime config, e.g. R2 endpoint, bucket name, HF Space URL, model names, and `KRILLINAI_DRY_RUN`.
- No `.env` files are used.

See `docs/ENVIRONMENT.md` for the complete list.

## Branch and environment mapping

| Layer | Development | Production |
|-------|-------------|------------|
| GitHub branch | `master` | `working-branch` |
| Cloudflare Worker | Dev Worker configured by variables/secrets | Prod Worker configured by variables/secrets |
| Hugging Face Space | `krillin-asr-dev` via `HF_SPACE_URL` | `krillin-asr-prod` via `HF_SPACE_URL` |
| R2 bucket | Dev bucket via `CF_R2_BUCKET` | Prod bucket via `CF_R2_BUCKET` |

The code does not hardcode environment names; resource names are selected through variables/secrets.

## TODO

- Implement real R2 upload/download and `head_object` exists checks.
- Implement HF Space `/transcribe` multipart call.
- Implement Gemini translation and TTS.
- Implement FFmpeg render pipeline.
- Implement Telegram video upload.
- Implement Google Drive upload.
- Future enhancement: add Cloudflare Queue for load control and retries.

## Project Documents

New AI agents should read the following documents in order:

1. **`docs/PROJECT_STATE.md`** — Current project state, blockers, and next task.
2. **`docs/DECISIONS.md`** — Architectural decisions log. Read this before making any structural changes.
3. **`docs/AGENT_ONBOARDING.md`** — Standard handoff procedure for AI agents.
4. **`TODOList.md`** — Development roadmap with milestones, tasks, and progress.
5. **`docs/ARCHITECTURE.md`** — This file. Architecture overview, R2 layout, idempotency.
6. **`docs/ENVIRONMENT.md`** — Environment variables reference (Secrets vs Variables classification).
7. **`docs/DEPLOYMENT.md`** — Deployment instructions and version pinning.
8. **`docs/VERSIONS.md`** — Version matrix for all dependencies.

All documents are kept at the repository root (`TODOList.md`) or under `docs/`.
