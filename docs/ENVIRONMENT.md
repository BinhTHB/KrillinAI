# KrillinAI v2 Environment Variables Reference

All configuration is read directly from environment variables. The project does **not** use `.env` files.

Rule:

- Put only sensitive values in **Secrets**.
- Put non-sensitive configuration in **Variables / Environment Variables**.
- Do not hardcode credentials in code, workflows, Worker config, or docs.

## GitHub Actions Secrets

Set under GitHub repository → Settings → Secrets and variables → Actions → Secrets.

| Name | Used by | Description |
|------|---------|-------------|
| `CF_R2_ACCESS_KEY_ID` | `R2Client` | Cloudflare R2 access key ID. Sensitive. |
| `CF_R2_SECRET_ACCESS_KEY` | `R2Client` | Cloudflare R2 secret access key. Sensitive. |
| `TELEGRAM_BOT_TOKEN` | `TelegramClient` | Telegram Bot API token. Sensitive. |
| `GEMINI_API_KEY` | `GeminiClient` | Google Gemini API key. Sensitive. |
| `GOOGLE_DRIVE_CREDENTIALS` | `GoogleDriveClient` | Google Service Account JSON credentials. Sensitive. |

## GitHub Actions Variables

Set under GitHub repository → Settings → Secrets and variables → Actions → Variables.

| Name | Used by | Description |
|------|---------|-------------|
| `KRILLINAI_DRY_RUN` | All workflows | Development/testing only. Use `true` to run placeholders and avoid real API calls. Production should set `false` or omit once real integrations are complete. |
| `CF_R2_ENDPOINT` | `R2Client` | Cloudflare R2 S3-compatible endpoint. Non-sensitive. |
| `CF_R2_BUCKET` | `R2Client` | Cloudflare R2 bucket name. Non-sensitive. |
| `HF_SPACE_URL` | `HuggingFaceClient` | Base URL of the selected Hugging Face Space. Non-sensitive. |
| `WHISPER_MODEL` | `HuggingFaceClient` / HF Space | ASR model name. Free-tier default is `base`. Non-sensitive. |
| `GEMINI_MODEL` | `GeminiClient` | Gemini model name. Non-sensitive. |
| `GOOGLE_DRIVE_FOLDER_ID` | `GoogleDriveClient` | Target Google Drive folder ID. Non-sensitive but operationally private. |

## Cloudflare Worker Secrets

Set in Cloudflare Dashboard → Worker → Settings → Variables and Secrets → Secrets.

| Name | Description |
|------|-------------|
| `GITHUB_TOKEN` | GitHub token used by Worker to dispatch `telegram_video_ingest`. Sensitive. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token used for webhook replies. Sensitive. |

## Cloudflare Worker Variables

Set in Cloudflare Dashboard or `worker/wrangler.toml`.

| Name | Description |
|------|-------------|
| `GITHUB_OWNER` | GitHub username/org. Non-sensitive. |
| `GITHUB_REPO` | GitHub repository name. Non-sensitive. |
| `GITHUB_DISPATCH_EVENT` | Initial event type, usually `telegram_video_ingest`. Non-sensitive. |
| `GITHUB_API_URL` | GitHub API base URL, usually `https://api.github.com`. Non-sensitive. |
| `TELEGRAM_API_URL` | Telegram API base URL, usually `https://api.telegram.org/bot`. Non-sensitive. |

## Hugging Face Space Secrets

Current skeleton does not require HF Space secrets. Add secrets only if the future ASR service calls external protected APIs.

## Hugging Face Space Environment Variables

Set in Hugging Face Space → Settings → Variables.

| Name | Description |
|------|-------------|
| `WHISPER_MODEL` | Faster-Whisper model to load. Default: `base`. |
| `WHISPER_DEVICE` | Runtime device. Default: `cpu`. |
| `WHISPER_COMPUTE_TYPE` | Compute type. Default: `int8`. |

GPU production deployments may override these values with `WHISPER_MODEL=distil-large-v3`, `WHISPER_DEVICE=cuda`, and `WHISPER_COMPUTE_TYPE=float16` without code changes.
| `PORT` | FastAPI port. Default: `7860`. |

## Dev / Production Mapping

| Layer | Development | Production |
|-------|-------------|------------|
| GitHub branch | `master` | `working-branch` |
| Cloudflare Worker | Worker configured for dev environment | Worker configured for prod environment |
| Hugging Face Space | `krillin-asr-dev` via `HF_SPACE_URL` | `krillin-asr-prod` via `HF_SPACE_URL` |
| R2 bucket | Dev bucket via `CF_R2_BUCKET` | Prod bucket via `CF_R2_BUCKET` |

Names are examples. The code reads all environment-specific values from variables/secrets and does not hardcode dev/prod resource names.
