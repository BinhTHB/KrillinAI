# Changelog

All significant changes to KrillinAI v2 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- Project state tracking via `docs/PROJECT_STATE.md`.
- Architecture decision log via `docs/DECISIONS.md`.
- Agent onboarding procedure via `docs/AGENT_ONBOARDING.md`.
- Version matrix reference via `docs/VERSIONS.md`.
- Development roadmap via `TODOList.md` (standardized milestone template).
- Milestone 2 R2 client implementation with boto3 lazy initialization, `head_object` existence checks, upload/download methods, and dry-run tests.
- `scripts/v2/tests/test_r2_client.py` for R2 mock round-trip and metadata persistence checks.

### Changed

- Restructured `TODOList.md` with Status, Estimated Effort, Dependencies, Review Checklist per milestone.
- Standardized Secrets vs Variables classification across documentation.
- Documented dev/production mapping in `ARCHITECTURE.md` and `ENVIRONMENT.md`.
- `scripts/v2/config.py` now supports both `CF_R2_*` and `R2_*` environment variable prefixes, plus R2 region configuration.

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

- Cloudflare Worker (`worker/`) for Telegram webhook + GitHub dispatch.
- Hugging Face Space skeleton (`hf-space/`) with FastAPI (`/health`, `/transcribe`).
- Three GitHub Actions workflows:
  - `ingest.yml` — download video, extract audio, upload to R2.
  - `ai_pipeline.yml` — transcription, alignment, translation, TTS.
  - `render.yml` — blur subtitles, overlay, audio mux.
- Shared modules in `scripts/v2/`:
  - `config.py` — environment variable loader.
  - `logger.py`, `retry.py` — utilities.
  - `models.py` — job metadata, status, stage.
  - `layout.py` — canonical R2 storage layout.
  - Client placeholders: `r2_client.py`, `telegram_client.py`, `github_client.py`, `hf_client.py`, `gemini_client.py`, `gdrive_client.py`.
- Workflow orchestrators: `scripts/v2/workflows/ingest.py`, `ai_pipeline.py`, `render.py`.
- Step-level idempotency via `r2_client.exists()`.
- `config/config-example.toml` — updated with `[serverless_v2]` section.

---

[Unreleased]: https://github.com/BinhTHB/KrillinAI/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/BinhTHB/KrillinAI/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/BinhTHB/KrillinAI/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BinhTHB/KrillinAI/releases/tag/v0.1.0
