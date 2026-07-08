# Changelog

All significant changes to KrillinAI v2 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- Unified Go CLI pipeline workflow (`.github/workflows/ai_pipeline.yml`) running `krillinai-cli pipeline` locally on the GitHub Actions runner.
- Helper script `scripts/v2/workflows/go_pipeline_io.py` to handle Cloudflare R2 and Telegram I/O around the Go pipeline.
- Cloudflare Worker deployment guide with required Worker secrets, variables, Telegram webhook setup, and live entry-point validation checklist.
- Architecture decision DEC-012 separating code implementation, infrastructure deployment, and operational validation states.
- Project state tracking via `docs/PROJECT_STATE.md`.
- Architecture decision log via `docs/DECISIONS.md`.
- Agent onboarding procedure via `docs/AGENT_ONBOARDING.md`.
- Version matrix reference via `docs/VERSIONS.md`.
- Development roadmap via `TODOList.md` (standardized milestone template).
- Milestone 2 R2 client implementation with boto3 lazy initialization, `head_object` existence checks, upload/download methods, and dry-run tests.
- `scripts/v2/tests/test_r2_client.py` for R2 mock round-trip and metadata persistence checks.
- Milestone 4 HF client implementation with `/health` polling and multipart `/transcribe` upload.
- `scripts/v2/tests/test_hf_client.py` for Hugging Face client dry-run health and transcription checks.
- Hugging Face CPU Free Tier deployment support for `hf-space/`.
- Milestone 5 Gemini translation and native Live API TTS integration.
- Milestone 6 FFmpeg render pipeline with subtitle-region blur, translated SRT overlay, and TTS audio muxing.
- `scripts/v2/render_ffmpeg.py` for reusable FFmpeg render command construction and execution.
- Render workflow dry-run and FFmpeg command tests.
- Milestone 7 Telegram `sendVideo` upload and Google Drive file upload delivery clients.
- `scripts/v2/tests/test_telegram_client.py` and `scripts/v2/tests/test_gdrive_client.py` for delivery client dry-run checks.
- `scripts/v2/tests/test_gemini_client.py` for Gemini translation and TTS dry-run checks.
- `scripts/v2/tests/test_real_pipeline.py` for real R2, Gemini, and FFmpeg smoke checks using local credentials.
- R2 presigned download URL generation for large final video delivery.

### Changed
- GitHub Actions workflows now select the `development` or `production` environment by branch, prefer standardized `R2_*` variables, and expose legacy `CF_R2_*` fallback variables during migration.
- Configured GitHub Actions development and production environments, set target environment secrets/variables, and updated remote secrets/variables using GitHub CLI.
- Dev Cloudflare Worker renamed from `krillin-ai-worker` to `krillin-ai-worker-dev`.
- Production Cloudflare Worker `krillin-ai-worker-prod` deployed, production Worker secrets configured, and Telegram production webhook set to `/webhook/telegram`.
- Deployment guide now requires pushing `working-branch` before production deployment and validation, and documents environment-driven Dev/Production separation.
- Standardized ASR compute on GitHub Actions Go CLI (no HF Space) to run WhisperX locally on runner.
- Replaced Python-based AI Pipeline (`ai_pipeline.py`) and Render (`render.py`) with unified Go CLI execution for Telegram pipeline.
- Disabled `repository_dispatch` auto-trigger for `render.yml` to make it manual-only.
- Gemini SRT translation now retries transient API failures with exponential backoff and uses a 300s read timeout to avoid failing long subtitle translations.
- Ingest workflow now falls back to `f2` for Douyin downloads when `yt-dlp` rejects fresh cookies; validated by Workflow #1 run `28851614314`.
- Ingest workflow now passes optional `YT_DLP_COOKIES` from GitHub Secrets to `yt-dlp`, enabling authenticated Douyin/TikTok downloads when fresh cookies are required.
- Deployment guide now documents how to export Douyin/TikTok cookies and store them as the `YT_DLP_COOKIES` GitHub Actions Secret.
- `scripts/v2/workflows/ingest.py` now catches `yt-dlp` and FFmpeg failures, stores failed metadata, and sends a human-readable Telegram error message.
- Cloudflare Worker entry point deployed and validated at `https://krillin-ai-worker-dev.yhomha1111.workers.dev`; Telegram webhook configured to `/webhook/telegram`.
- `worker/wrangler.toml` now includes non-sensitive production defaults for GitHub dispatch and Telegram API URL while keeping secrets out of source control.
- Project state now marks Telegram entry as operationally validated for development after Worker health, webhook setup, and repository_dispatch trigger checks passed.
- Project state now separates Code Status, Deployment Status, and Operational Validation Status.
- Restructured `TODOList.md` with Status, Estimated Effort, Dependencies, Review Checklist per milestone.
- Standardized Secrets vs Variables classification across documentation.
- Documented dev/production mapping in `ARCHITECTURE.md` and `ENVIRONMENT.md`.
- `scripts/v2/config.py` now prefers `R2_*` and temporarily falls back to legacy `CF_R2_*` variables during migration.
- `scripts/v2/hf_client.py` now calls the HF Space API instead of raising `NotImplementedError`.
- `scripts/v2/gemini_client.py` now uses Gemini REST for SRT translation and Gemini Live API (`gemini-3.1-flash-live-preview`) for text-to-audio synthesis.
- `.github/workflows/ai_pipeline.yml` now installs `google-genai` and passes `GEMINI_TTS_MODEL`.
- `scripts/v2/workflows/render.py` now calls the real FFmpeg render helper outside dry-run mode instead of copying the source video placeholder.
- `scripts/v2/workflows/render.py` now uploads small final videos to Telegram and routes files over 50 MB to 24-hour R2 presigned URLs.
- `.github/workflows/render.yml` no longer installs Google Drive API client dependencies for the default large-file delivery path.

---

## [0.2.0] — 2026-07-05 — Documentation System

### Added
- `docs/ARCHITECTURE.md` — pipeline overview, R2 layout, idempotency, environment mapping.
- `docs/DEPLOYMENT.md` — deployment guide with version pinning and environment mapping.
- `docs/ENVIRONMENT.md` — environment variables reference (Secrets vs Variables).
- `docs/VERSIONS.md` — version matrix for all dependencies.

---

## [0.1.1] — 2026-07-05 — Standardised Workflows and Docs

### Added
- `docs/` directory with deployment and environment setup documentation.
- Environment classification rules (Secrets vs Variables).

### Changed
- Workflow triggering switched from `workflow_run` to `repository_dispatch` for multi-branch support.
- Removed `scripts/v2/pipeline_step.py` — moved orchestration entirely into `scripts/v2/workflows/`.
- Upgraded `r2_client.py` with `exists()` for step-level idempotency.
- Updated workflows to use `vars.*` instead of `secrets.*` for non‑sensitive configurations.
- Moved `CF_R2_BUCKET`, `CF_R2_ENDPOINT`, `KRILLINAI_DRY_RUN` from Secrets to Variables.

---

## [0.1.0] — 2026-07-05 — Skeleton v2

### Added
- Basic project structure and workflow configurations.











