# KrillinAI v2 Deployment Guide

This guide covers deploying the serverless KrillinAI v2 pipeline.

## Prerequisites

- GitHub repository with Actions enabled.
- Cloudflare account (Workers + R2).
- Hugging Face Space (GPU recommended).
- Google Cloud project with Drive API enabled (optional).
- Telegram Bot token.

## GitHub repository setup

### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret name | Description |
|-------------|-------------|
| `KRILLINAI_DRY_RUN` | Set to "true" for dry-run, "false" for real execution. |
| `CF_R2_ACCESS_KEY_ID` | Cloudflare R2 access key ID. |
| `CF_R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret access key. |
| `CF_R2_ENDPOINT` | R2 S3-compatible endpoint URL. |
| `CF_R2_BUCKET` | R2 bucket name. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token. |
| `GEMINI_API_KEY` | Google Gemini API key. |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Service Account JSON (single-line) for Drive upload. |

### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable name | Description | Example |
|---------------|-------------|---------|
| `HF_SPACE_URL` | Hugging Face Space base URL. | `https://your-username-krillin-asr-prod.hf.space` |
| `WHISPER_MODEL` | Whisper model to use on HF Space. | `distil-large-v3` |
| `GEMINI_MODEL` | Gemini model for translation/TTS. | `gemini-1.5-flash` |
| `GOOGLE_DRIVE_FOLDER_ID` | Target Drive folder ID for large video uploads. | `1AbCdEfGh...` |

## Cloudflare Worker setup

Deploy `worker/` with Wrangler:

```bash
cd worker
npm install
wrangler deploy
```

### Worker environment variables (Dashboard → Worker → Settings → Variables and Secrets)

| Variable/Secret | Type | Value |
|-----------------|------|-------|
| `GITHUB_OWNER` | Variable | GitHub username/org. |
| `GITHUB_REPO` | Variable | Repository name. |
| `GITHUB_DISPATCH_EVENT` | Variable | `telegram_video_ingest` |
| `GITHUB_API_URL` | Variable | `https://api.github.com` |
| `GITHUB_TOKEN` | Secret | GitHub PAT with `repo` scope. |
| `TELEGRAM_BOT_TOKEN` | Secret | Telegram Bot token. |
| `TELEGRAM_API_URL` | Variable | `https://api.telegram.org/bot` |

### R2 bucket

Create a bucket (e.g., `krillinai-assets`) and note its endpoint, access key, secret. Put them in GitHub Secrets above.

### Telegram webhook

After Worker is deployed, set Telegram webhook to the Worker URL:

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<worker-name>.<account>.workers.dev/webhook/telegram
```

## Hugging Face Space

1. Create a Space → Docker → GPU (T4 or better).
2. Set the repository to deploy `hf-space/` (or push Docker image).
3. Space secrets:

| Secret | Value |
|--------|-------|
| `WHISPER_MODEL` | `distil-large-v3` (or `large-v3`) |
| `WHISPER_DEVICE` | `auto` |
| `WHISPER_COMPUTE_TYPE` | `float16` |

The Space exposes:

- `GET /health` → `{ "status": "ready", "model": "..." }`
- `POST /transcribe` (multipart `file`, optional `language`, `vad_filter`, `word_timestamps`) → SRT text.

## Branch strategy

- `master` → development. Sync with upstream via the commands in `AGENTS.md`.
- `working-branch` → production. Only merge from `master` when ready.

Workflow files run on both branches; secrets/variables are shared at org/repo level.

## Testing

Run dry-run locally or via workflow_dispatch:

```bash
# Dry run ingest
python scripts/v2/workflows/ingest.py --job-id test-1 --video-url "https://..." --chat-id 123 --message-id 456

# Dry run AI pipeline
python scripts/v2/workflows/ai_pipeline.py --job-id test-1 --chat-id 123 --message-id 456

# Dry run render
python scripts/v2/workflows/render.py --job-id test-1 --chat-id 123 --message-id 456
```

Set `KRILLINAI_DRY_RUN=true` (default) to skip real API calls.
