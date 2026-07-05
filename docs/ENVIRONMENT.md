# KrillinAI v2 Environment Variables Configuration Reference

All environment variables used across GitHub Actions, Cloudflare Worker, and Hugging Face Space.

## GitHub repository secrets

Must be set under Settings → Secrets and variables → Actions → Secrets.

| Secret name | Target module | Description |
|-------------|---------------|-------------|
| `KRILLINAI_DRY_RUN` | All Workflows | Set to "true" to skip real API calls and output mock data. |
| `CF_R2_ACCESS_KEY_ID` | R2 client | Cloudflare R2 Access Key ID. |
| `CF_R2_SECRET_ACCESS_KEY` | R2 client | Cloudflare R2 Secret Access Key. |
| `CF_R2_ENDPOINT` | R2 client | S3-compatible API endpoint URL for R2. |
| `CF_R2_BUCKET` | R2 client | Name of the R2 bucket. |
| `TELEGRAM_BOT_TOKEN` | Telegram / notify | API Token for the Telegram bot. |
| `GEMINI_API_KEY` | Gemini client | Google Gemini API key for translation and TTS. |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive client | Google Cloud Service Account JSON credentials. |

## GitHub repository variables

Must be set under Settings → Secrets and variables → Actions → Variables.

| Variable name | Target module | Description |
|---------------|---------------|-------------|
| `HF_SPACE_URL` | HF client | Base URL of the Hugging Face Space Transcription service. |
| `WHISPER_MODEL` | HF space / client | Model to request from the space (e.g., `distil-large-v3`, `large-v3`). |
| `GEMINI_MODEL` | Gemini client | Gemini model to use (default: `gemini-1.5-flash`). |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive client | Folder ID where large videos will be uploaded. |

## Cloudflare Worker settings

Must be set in wrangler.toml or Cloudflare dashboard.

### Variables

| Name | Description |
|------|-------------|
| `GITHUB_OWNER` | Owner of the GitHub repository (username or org). |
| `GITHUB_REPO` | Name of the GitHub repository. |
| `GITHUB_DISPATCH_EVENT` | Event type for dispatch (`telegram_video_ingest`). |
| `GITHUB_API_URL` | Base URL of GitHub API (`https://api.github.com`). |
| `TELEGRAM_API_URL` | Base URL of Telegram API (`https://api.telegram.org/bot`). |

### Secrets

| Name | Description |
|------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with actions write scope. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token. |

## Hugging Face Space settings

Must be set as Environment Variables / Secrets in the Hugging Face Space settings panel.

| Name | Description | Default / Example |
|------|-------------|-------------------|
| `WHISPER_MODEL` | Faster-Whisper model to load | `distil-large-v3` |
| `WHISPER_DEVICE` | Hardware device to use | `auto` (or `cuda`, `cpu`) |
| `WHISPER_COMPUTE_TYPE` | Floating point compute format | `float16` |
| `PORT` | Listening port for FastAPI | `7860` |

---

No real secrets are hardcoded in the codebase.
