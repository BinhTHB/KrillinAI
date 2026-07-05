# KrillinAI v2 Deployment Guide

## Prerequisites

- GitHub repository with Actions enabled.
- Cloudflare account (Workers + R2).
- Hugging Face account (Spaces).
- Google Cloud project with Drive API enabled (optional, for >50 MB videos).
- Telegram Bot token from @BotFather.

## Version Pinning

| Component | Version / Tag | Notes |
|-----------|---------------|-------|
| GitHub Actions runner | `ubuntu-latest` (22.04 LTS) | Managed by GitHub. |
| Python | `3.10` | Set via `actions/setup-python@v5`. |
| Node.js | `22.x` | For Cloudflare Worker local development and Wrangler. |
| Wrangler | `^3.0.0` | Worker deployment CLI. |
| Docker base image | `nvidia/cuda:12.1.0-runtime-ubuntu22.04` | Used in `hf-space/Dockerfile`. |
| FFmpeg | `7.x` (system package) | Installed on runner for audio extraction and render. |
| yt-dlp | latest | Video download tool, installed on runner. |
| Faster-Whisper | `>=1.0.0` | Runs inside HF Space, not on runner. |
| ctranslate2 | Bundled with faster-whisper | No separate pin required. |
| boto3 | latest | Python AWS SDK used for R2 (S3-compatible). |
| requests | latest | HTTP client for HF Space, Gemini API calls. |
| FastAPI | `>=0.100.0` | HF Space ASR service framework. |
| Uvicorn | `>=0.22.0` | ASGI server for HF Space. |

## GitHub repository setup

### Secrets

Set under Settings → Secrets and variables → Actions → Secrets.

| Name | Description |
|------|-------------|
| `CF_R2_ACCESS_KEY_ID` | Cloudflare R2 access key ID. |
| `CF_R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret access key. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token. |
| `GEMINI_API_KEY` | Google Gemini API key. |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Service Account JSON for Drive upload. |

### Variables

Set under Settings → Secrets and variables → Actions → Variables.

| Name | Description |
|------|-------------|
| `KRILLINAI_DRY_RUN` | Use "true" during development/testing to skip real API calls. Set to "false" or unset in production once integrations are ready. |
| `CF_R2_ENDPOINT` | Cloudflare R2 S3-compatible endpoint URL (non‑sensitive). |
| `CF_R2_BUCKET` | Name of the R2 bucket (non‑sensitive). |
| `HF_SPACE_URL` | Base URL of the Hugging Face Space, e.g. `https://your-krillin-asr-prod.hf.space`. |
| `WHISPER_MODEL` | ASR model name, default `distil-large-v3`. |
| `GEMINI_MODEL` | Gemini model for translation/TTS, default `gemini-1.5-flash`. |
| `GOOGLE_DRIVE_FOLDER_ID` | Target Google Drive folder ID. |

## Cloudflare Worker setup

```bash
cd worker
npm install
wrangler deploy
```

### Worker Secrets

| Name | Description |
|------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `actions:write` scope. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token. |

### Worker Variables

| Name | Description |
|------|-------------|
| `GITHUB_OWNER` | GitHub username or org. |
| `GITHUB_REPO` | Repository name. |
| `GITHUB_DISPATCH_EVENT` | Event type, usually `telegram_video_ingest`. |
| `GITHUB_API_URL` | `https://api.github.com` |
| `TELEGRAM_API_URL` | `https://api.telegram.org/bot` |

### R2 bucket

Create a bucket in Cloudflare Dashboard, generate R2 API tokens, and set `CF_R2_ACCESS_KEY_ID`, `CF_R2_SECRET_ACCESS_KEY`, `CF_R2_ENDPOINT`, `CF_R2_BUCKET` in GitHub Secrets and Variables.

### Telegram webhook

```text
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<worker>.<account>.workers.dev/webhook/telegram
```

## Hugging Face Space

1. Create a Space → Docker → GPU (T4 or better).
2. For development: name it `krillin-asr-dev`.
3. For production: name it `krillin-asr-prod`.
4. The Space name is **not** hardcoded; set `HF_SPACE_URL` in GitHub Variables accordingly.

### Space Environment Variables

Set in Space → Settings → Variables (not Secrets).

| Name | Default | Description |
|------|---------|-------------|
| `WHISPER_MODEL` | `distil-large-v3` | Faster-Whisper model to load. |
| `WHISPER_DEVICE` | `auto` | Device (`cuda`, `cpu`, `auto`). |
| `WHISPER_COMPUTE_TYPE` | `float16` | Compute type (`float16`, `int8_float16`, `int8`). |
| `PORT` | `7860` | FastAPI port. |

## Dev/Production deployment mapping

| Layer | Development | Production |
|-------|-------------|------------|
| GitHub branch | `master` | `working-branch` |
| GitHub Variables | `KRILLINAI_DRY_RUN=true`, dev HF/Drive URLs | `KRILLINAI_DRY_RUN=false` (or unset), prod URLs |
| Cloudflare Worker | Separate Worker deployment for dev | Separate Worker deployment for prod |
| Hugging Face Space | `krillin-asr-dev` | `krillin-asr-prod` |
| R2 bucket | Separate bucket for dev | Separate bucket for prod |

The code does **not** hardcode any of these names. All are read from environment variables at runtime.

## Testing

```bash
# Dry-run ingest (placeholders, no real API calls)
python scripts/v2/workflows/ingest.py --job-id test-1 --video-url "https://..." --chat-id 123 --message-id 456

# Dry-run AI pipeline
python scripts/v2/workflows/ai_pipeline.py --job-id test-1 --chat-id 123 --message-id 456

# Dry-run render
python scripts/v2/workflows/render.py --job-id test-1 --chat-id 123 --message-id 456
```

Set `KRILLINAI_DRY_RUN=true` in GitHub Variables (default) to skip real external calls.

### Trigger via workflow_dispatch in GitHub UI

Use the `workflow_dispatch` trigger on each workflow to run manually with test inputs.
