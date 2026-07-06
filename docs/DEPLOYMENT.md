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
| Docker base image | `python:3.10-slim` | CPU Free Tier default used in `hf-space/Dockerfile`. |
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
| `WHISPER_MODEL` | ASR model name, default `base` for CPU Free Tier. |
| `GEMINI_MODEL` | Gemini model for translation/TTS, default `gemini-1.5-flash`. |
| `GOOGLE_DRIVE_FOLDER_ID` | Target Google Drive folder ID. |

## Cloudflare Worker Deployment

The Cloudflare Worker is the Telegram entry point. It receives Telegram webhook updates at `POST /webhook/telegram`, validates the submitted video URL, replies to the user immediately, and triggers GitHub Actions through `repository_dispatch`.

Do not claim Telegram entry is operational until every validation item in this section passes.

### Worker implementation status

Implemented in `worker/src/index.js`:

- `POST /webhook/telegram` endpoint.
- Telegram `message` / `edited_message` parsing.
- Text-only URL extraction and validation for YouTube, TikTok, Douyin, X/Twitter, and direct video files.
- Immediate Telegram acknowledgement for valid URLs.
- Telegram error reply for unsupported text.
- GitHub `repository_dispatch` call using `GITHUB_TOKEN`.
- Worker console logging for webhook errors.

Known operational limits:

- The Worker does not process Telegram file uploads directly; users must send a supported URL.
- Failed `repository_dispatch` calls return HTTP 500 to Telegram and are logged in Cloudflare Worker logs.

### Install dependencies

```bash
cd worker
npm install
```

### Authenticate Wrangler

```bash
npx wrangler login
```

### Configure Worker variables

Non-sensitive defaults are set in `worker/wrangler.toml`. Override them in Cloudflare Dashboard → Workers & Pages → `krillin-ai-worker` → Settings → Variables and Secrets → Variables when deploying a different repo or environment.

| Name | Required | Example | Description |
|------|----------|---------|-------------|
| `GITHUB_OWNER` | Yes | `BinhTHB` | GitHub user or org that owns the repository. |
| `GITHUB_REPO` | Yes | `KrillinAI` | Repository name. |
| `GITHUB_DISPATCH_EVENT` | Yes | `telegram_video_ingest` | Initial GitHub event type consumed by `.github/workflows/ingest.yml`. |
| `GITHUB_API_URL` | Yes | `https://api.github.com` | GitHub API base URL. |
| `TELEGRAM_API_URL` | Yes | `https://api.telegram.org/bot` | Telegram Bot API base URL. |

### Configure Worker secrets

Set sensitive values with Wrangler or Cloudflare Dashboard. Do not hardcode them in `wrangler.toml`.

| Name | Description |
|------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `actions:write` scope. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token. |

Wrangler commands:

```bash
cd worker
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put TELEGRAM_BOT_TOKEN
```

### Deploy Worker

```bash
cd worker
npx wrangler deploy
```

Expected Worker URL:

```text
https://krillin-ai-worker.<cloudflare-subdomain>.workers.dev
```

If a custom domain or route is configured in Cloudflare, use that URL instead.

### Configure Telegram webhook

Replace `<TOKEN>` and `<WORKER_URL>`:

```text
https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>/webhook/telegram
```

Example:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://krillin-ai-worker.<cloudflare-subdomain>.workers.dev/webhook/telegram"
```

### Verify Telegram webhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Expected:

- `url` equals `<WORKER_URL>/webhook/telegram`.
- `last_error_message` is absent or empty.
- `pending_update_count` does not continuously increase after sending test messages.

### Verify Worker health

The Worker currently accepts only `POST` requests globally, so `GET /health` returns `405 Method Not Allowed`. Verify health with:

```bash
curl -X POST "<WORKER_URL>/health"
```

Expected response:

```json
{"status":"ok"}
```

### Validate Telegram entry point

Run this checklist after deployment:

- [ ] Worker deployed.
- [ ] Worker URL reachable with `POST /health`.
- [ ] Telegram webhook configured with `/webhook/telegram`.
- [ ] `getWebhookInfo` returns the correct webhook URL and no recent error.
- [ ] Sending a supported video URL to the Telegram bot produces an acknowledgement message.
- [ ] Cloudflare Worker logs show the webhook request.
- [ ] GitHub `repository_dispatch` is triggered with event `telegram_video_ingest`.
- [ ] GitHub workflow `ingest.yml` starts.

Supported test message examples:

```text
https://www.youtube.com/watch?v=<id>
https://youtu.be/<id>
https://www.tiktok.com/@user/video/<id>
https://x.com/user/status/<id>
https://example.com/video.mp4
```

If the bot does not respond, check in order:

1. `getWebhookInfo` for Telegram webhook errors.
2. Cloudflare Worker logs for `webhook error`.
3. Worker secrets: `TELEGRAM_BOT_TOKEN`, `GITHUB_TOKEN`.
4. Worker variables: `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_DISPATCH_EVENT`, `GITHUB_API_URL`, `TELEGRAM_API_URL`.
5. GitHub token permissions for repository dispatch / Actions.

### R2 bucket

Create a bucket in Cloudflare Dashboard, generate R2 API tokens, and set `CF_R2_ACCESS_KEY_ID`, `CF_R2_SECRET_ACCESS_KEY`, `CF_R2_ENDPOINT`, `CF_R2_BUCKET` in GitHub Secrets and Variables.

## Hugging Face Space

1. Create a Space → Docker → CPU Basic (Free).
2. For development: name it `krillin-asr-dev`.
3. For production: name it `krillin-asr-prod`.
4. The Space name is **not** hardcoded; set `HF_SPACE_URL` in GitHub Variables accordingly.
5. GPU is optional for future scaling only; the system architecture remains unchanged.

### Space Environment Variables

Set in Space → Settings → Variables (not Secrets).

| Name | Default | Description |
|------|---------|-------------|
| `WHISPER_MODEL` | `base` | Faster-Whisper model to load on CPU Free Tier. |
| `WHISPER_DEVICE` | `cpu` | Device for free-tier deployment. |
| `WHISPER_COMPUTE_TYPE` | `int8` | CPU-friendly compute type. |
| `PORT` | `7860` | FastAPI port. |

### Optional GPU production overrides

Paid GPU deployments may override these variables without code changes:

```text
WHISPER_MODEL=distil-large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

## Dev/Production deployment mapping

| Layer | Development | Production |
|-------|-------------|------------|
| GitHub branch | `master` | `working-branch` |
| GitHub Variables | `KRILLINAI_DRY_RUN=true`, dev HF/Drive URLs | `KRILLINAI_DRY_RUN=false` (or unset), prod URLs |
| Cloudflare Worker | Separate Worker deployment for dev | Separate Worker deployment for prod |
| Hugging Face Space | Docker CPU Basic (Free), `krillin-asr-dev` | Docker CPU Basic by default; optional paid GPU override, `krillin-asr-prod` |
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
