# KrillinAI v2 Deployment Guide

## Prerequisites

- GitHub repository with Actions enabled.
- Cloudflare account (Workers + R2).
- Hugging Face account (Spaces).
- Google Cloud project with Drive API enabled (optional, for >50 MB videos).
- Telegram Bot token from @BotFather.

## Production Release Process

Use this process when `master` has been validated and is ready to be promoted to `working-branch`.

### Branch strategy

`working-branch` is the production snapshot of `master`.

After each release:

- Merge `master` into `working-branch`.
- Keep both branches aligned in logic, source code, workflow files, and project structure.
- Allow differences only in commit history and release state.
- Do not maintain two branches with different application logic.

`master` remains the development and upstream synchronization branch. `working-branch` remains the production branch. Production is only updated after `working-branch` is pushed to GitHub.

### Configuration strategy

Do not separate Development and Production by source code or branch-specific code edits.

Development and Production differences must be managed only through environment configuration:

- GitHub Secrets
- GitHub Variables
- Cloudflare Worker Secrets
- Cloudflare Worker Variables
- Telegram Bot Token
- Cloudflare R2 Bucket
- Cloudflare R2 Endpoint
- Gemini API Key
- Worker URL
- Telegram Webhook URL
- Other environment-specific values

Do not hardcode production values or maintain production-only source changes.

### Release flow

```powershell
git checkout master
git status
git pull origin master

git checkout working-branch
git status
git pull origin working-branch

git merge master --no-ff -m "release: promote validated master to production"
```

After the merge, complete review before pushing:

```powershell
git diff origin/working-branch..working-branch
git status
```

Review checklist before push:

- Review diff and branch status.
- Run secret scan or manually verify no secrets, cookies, tokens, credentials, `.env`, or generated sensitive files are included.
- Review workflow and config changes.
- Confirm production configuration remains environment-driven.

Then push the production branch before any deploy or production validation:

```powershell
git push origin working-branch
```

This order is required because `working-branch` is the production branch. Production validation must run only against a version that already exists on the remote production branch.

After push:

1. Configure production GitHub Variables and Secrets if needed.
2. Deploy Cloudflare Worker production.
3. Configure Telegram production webhook.
4. Run production E2E validation.
5. Verify GitHub Actions, Worker logs, R2 output, and Telegram delivery.
6. Update `PROJECT_STATE.md`, `CHANGELOG.md`, and `TODOList.md`.

### Short deployment flow

```text
master stable
    ↓
merge master -> working-branch
    ↓
review diff + secret scan
    ↓
push working-branch
    ↓
configure production vars/secrets (nếu cần)
    ↓
deploy Cloudflare Worker production
    ↓
set Telegram production webhook
    ↓
run production E2E test
    ↓
verify GitHub Actions, Worker logs, R2, Telegram
    ↓
update PROJECT_STATE.md
update CHANGELOG.md
update TODOList.md
```

### Release notes

- Review diff and secret scan must complete before push.
- Production validation must happen only after the production branch on GitHub contains the release version.
- If production validation succeeds, creating a Git tag is recommended for traceability and rollback, but it is not required.

### Cloudflare Worker source policy

Do not create separate Dev and Production Worker source implementations.

Prefer:

- The same Worker source code.
- Multiple environments (`dev`, `production`) or deployment configuration.
- Environment-specific Worker Secrets and Variables.

Do not maintain two configuration files with different logic unless there is a real operational need.

### GitHub Actions policy

Workflows on `master` and `working-branch` should stay the same.

Do not create a production-only workflow just because tokens, buckets, or endpoints differ. Workflows must use the same logic and read values from GitHub Secrets/Variables for the relevant branch or environment.

### Telegram policy

Telegram Dev and Production differ only by:

- Bot Token
- Webhook URL

Webhook processing logic must stay shared.

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

The Cloudflare Worker is the intended Telegram entry point after deployment and operational validation. Source code alone does not prove the Telegram entry is live.

Do not claim Telegram entry is operational until every validation item in this section passes.

### Worker code verification

Verified against `worker/src/index.js`:

| Feature | Implemented | Evidence | Missing |
|---------|-------------|----------|---------|
| Supported HTTP method | Yes | `if (request.method !== 'POST') return 405` | `GET` requests are intentionally rejected. |
| Health route | Yes | `url.pathname === '/health'` returns `{"status":"ok"}` | Only works with `POST /health`. |
| Telegram webhook route | Yes | `url.pathname === '/webhook/telegram'` | None. |
| Telegram update parsing | Yes | `const msg = body.message || body.edited_message` | Non-text messages are ignored. |
| URL validation | Yes | `validateVideoUrl(text)` supports YouTube, TikTok/Douyin, Twitter/X, direct video file URLs | Telegram file uploads are not supported. |
| Invalid message reply | Yes | Calls `replyTelegram(...)` with invalid-link message | Requires valid `TELEGRAM_BOT_TOKEN`. |
| Immediate valid URL acknowledgement | Yes | Calls `replyTelegram(...)` before GitHub dispatch | Requires valid `TELEGRAM_BOT_TOKEN`. |
| GitHub repository dispatch | Yes | `POST ${GITHUB_API_URL}/repos/${owner}/${repo}/dispatches` | Requires valid `GITHUB_TOKEN` permissions. |
| Success status update | Yes | Sends `Đã khởi tạo pipeline xử lý...` after dispatch succeeds | Not sent if dispatch fails. |
| Error logging | Yes | `console.error('webhook error:', err)` | Telegram does not receive a failure message when dispatch throws. |

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
| `GITHUB_TOKEN` | GitHub Personal Access Token allowed to call `POST /repos/{owner}/{repo}/dispatches`. Classic PAT: `repo` for private repositories or `public_repo` for public repositories. Fine-grained PAT: repository access with Contents write permission. |
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

### Operational Validation

Run this checklist after deployment:

- [ ] Worker deployed.
- [ ] Worker URL reachable with `POST /health`.
- [ ] Telegram webhook configured with `/webhook/telegram`.
- [ ] `getWebhookInfo` returns the correct URL.
- [ ] Telegram request reaches Worker.
- [ ] Invalid message receives expected reply.
- [ ] Valid URL receives acknowledgement.
- [ ] `repository_dispatch` succeeds.
- [ ] GitHub workflow `ingest.yml` starts.
- [ ] First workflow logs are visible.
- [ ] Telegram receives status update.

Only after every item passes may Telegram be considered the production entry point.

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
| Cloudflare Worker | Same source, dev deployment/config | Same source, production deployment/config |
| Hugging Face Space | Docker CPU Basic (Free), `krillin-asr-dev` | Docker CPU Basic by default; optional paid GPU override, `krillin-asr-prod` |
| R2 bucket | Separate bucket for dev | Separate bucket for prod |

The code does **not** hardcode any of these names. All differences are read from environment variables, GitHub Secrets/Variables, Cloudflare Worker Secrets/Variables, and service configuration at runtime.

## Douyin/TikTok cookies for yt-dlp

Some Douyin/TikTok videos cannot be downloaded by `yt-dlp` without fresh browser cookies. R2 does not solve this because R2 only stores files after a successful download; the blocked step is the initial download from Douyin.

Preferred setup:

1. Log in to Douyin/TikTok in a browser.
2. Export cookies for `douyin.com` / `tiktok.com` in Netscape format as `cookies.txt`.
3. Save the full text content of `cookies.txt` as a GitHub Actions Secret named `YT_DLP_COOKIES`.
4. Re-run the ingest workflow or send the Telegram link again.

The ingest workflow passes `YT_DLP_COOKIES` into `scripts/v2/workflows/ingest.py`; the script writes it to a temporary `workdir/{job_id}/cookies.txt` and calls:

```bash
yt-dlp --cookies workdir/<job_id>/cookies.txt ...
```

Local fallback:

- Put a Netscape-format `cookies.txt` file at the repository root.
- Run `python scripts/v2/workflows/ingest.py ...` locally.

Do not commit cookie files. They contain authenticated browser sessions.

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
