# KrillinAI v2 — Architectural Decisions Log

This document records the architectural and technical decisions made during the design and implementation of KrillinAI v2.

---

## DEC-001: Serverless Event-Driven Architecture

- **Status**: Accepted
- **Context**: KrillinAI v1 ran as a local monolith or standard VPS. This incurred high 24/7 hosting costs, and was not resilient to API limits or runner outages.
- **Decision**: Redesign the entire backend into a serverless, event‑driven pipeline: Telegram webhook → Cloudflare Worker API Gateway → GitHub Actions runner orchestration → Cloudflare R2 storage → Hugging Face Space (CPU Free Tier; GPU optional) / Gemini API → Telegram / Google Drive delivery.
- **Reason**: Near‑zero cost at idle, highly scaleable, automatic retry isolation, and bypasses local hardware constraints.
- **Impact**: All state and logic must be split into sequential, stateless phases.

---

## DEC-002: Cloudflare Worker + GitHub Actions for Orchestration

- **Status**: Accepted
- **Context**: We need a serverless scheduler to run python/FFmpeg steps without maintaining a VM.
- **Decision**: Use Cloudflare Workers as the lightweight API Gateway (cold start < 10ms), and GitHub Actions free runners (2 vCPUs, 7 GB RAM, 84 GB storage) to run the heavy lifters (yt-dlp, FFmpeg, boto3).
- **Reason**: Completely free tier available for both platforms, and GitHub Actions natively supports python/docker steps with standard runners.
- **Impact**: Latency of GitHub Actions start (typically 10s–30s) must be acceptable to users.

---

## DEC-003: repository_dispatch instead of workflow_run

- **Status**: Accepted
- **Context**: Workflows need to execute sequentially (Ingest → AI → Render). Initially, `workflow_run` (on completion of previous workflow) was considered.
- **Decision**: Chain workflows actively by sending a GitHub `repository_dispatch` API call at the end of each workflow to start the next one.
- **Reason**: `workflow_run` triggers only on the default branch (`master`), making development and testing on feature branches or `working-branch` impossible. Active dispatch via `repository_dispatch` works on any branch matching the dispatch token scope.
- **Impact**: Requires storing and calling GitHub Actions API tokens within the workflows.

---

## DEC-004: No `.env` Files

- **Status**: Accepted
- **Context**: Devs often use `.env` files locally to store configuration, but this leads to secret leak risks and inconsistency in CI.
- **Decision**: Read all configuration directly from environment variables. Do **not** parse or look for `.env` files in the codebase.
- **Reason**: Standardizes dev, CI/CD, and production runtime environments. Avoids credential leakage.
- **Impact**: Devs must set variables in their terminal session or wrapper scripts.

---

## DEC-005: Strict GitHub Secrets vs Variables Classification

- **Status**: Accepted
- **Context**: Over‑classifying configs as Secrets makes it harder to debug/adjust variables like model names, bucket names, and endpoints.
- **Decision**:
  - **Secrets** (highly sensitive): tokens, API keys, Google Drive JSON, Cloudflare access keys.
  - **Variables** (non‑sensitive configuration): `R2_BUCKET`, `R2_ENDPOINT`, `HF_SPACE_URL`, `WHISPER_MODEL`, `GEMINI_MODEL`, `GOOGLE_DRIVE_FOLDER_ID`, `KRILLINAI_DRY_RUN`.
- **Reason**: Increases visibility of non-sensitive parameters in GitHub Actions UI.
- **Impact**: Environment variables must be bound correctly to `secrets.*` or `vars.*` in workflow files.

---

## DEC-006: Branch Strategy (master vs working-branch)

- **Status**: Accepted
- **Context**: Align with local codebase branch setup and upstream sync requirements.
- **Decision**:
  - `master` = Development and sync upstream.
  - `working-branch` = Production.
- **Reason**: Keeps Master in sync with original upstream codebase `https://github.com/krillinai/KrillinAI.git`, while keeping fork‑specific production deployments stable on `working-branch`.
- **Impact**: Releases/production deployments must target `working-branch`.

---

## DEC-007: No Cloudflare Queue at MVP

- **Status**: Accepted
- **Context**: A message queue is useful to throttle heavy traffic, but adds complexity.
- **Decision**: Defer Cloudflare Queue integration to future backlog. The MVP uses direct dispatch.
- **Reason**: YAGNI (You Aren't Gonna Need It) for early testing. Focus on the core pipeline first.
- **Impact**: If multiple users send videos simultaneously, multiple parallel GitHub Actions runs will trigger immediately.

---

## DEC-008: Idempotency Per Step

- **Status**: Accepted
- **Context**: If Workflow #3 (Render) fails, we do not want to download, transcribe, translate, and synthesize TTS again.
- **Decision**: Implement `exists(key)` check in R2 Client. Each workflow step checks for its specific output key before performing work. If key exists, it downloads the asset and skips the process.
- **Reason**: Drastically cuts AI execution costs, reduces runtime, and makes restarts resilient.
- **Impact**: Output file naming conventions must be fixed and deterministic under `jobs/{job_id}/`.

---

## DEC-009: Workflows as Orchestration Only

- **Status**: Accepted
- **Context**: Spreading python/shell commands directly inside GitHub Actions YAML makes it hard to test locally.
- **Decision**: Actions step YAML should only execute orchestrator python scripts: `ingest.py`, `ai_pipeline.py`, `render.py`. Business logic belongs inside `scripts/v2/`.
- **Reason**: Code remains testable locally with python execution and dry-run flags.
- **Impact**: YAML files remain very clean and short.

---

## DEC-010: Shared Modules for External Services

- **Status**: Accepted
- **Context**: Subcommands in `pipeline_step.py` duplicated API logic and were hard to structure.
- **Decision**: Remove `pipeline_step.py`. Tightly bundle all client code into reusable object‑oriented wrappers: `R2Client`, `TelegramClient`, `GitHubClient`, `HuggingFaceClient`, `GeminiClient`, `GoogleDriveClient`.
- **Reason**: Encourages code reuse, modular unit testing, and decouples workflow scripts from direct HTTP requests.
- **Impact**: Easier to mock external calls in unit tests.

---

## DEC-011: R2 Presigned URLs for Large-File Delivery

- **Status**: Accepted
- **Context**: Telegram Bot API delivery is limited to small files, while Google Drive Service Account uploads require quota or Shared Drive setup that does not fit the 100% free project constraint.
- **Decision**: Deliver final videos over Telegram when they are at most 50 MB; for larger files, keep the final video in Cloudflare R2 and send the user a 24-hour presigned download URL.
- **Reason**: R2 is already part of the pipeline, avoids Google Drive quota issues, preserves private bucket access, and stays within the free serverless architecture.
- **Impact**: `render.py` no longer depends on Google Drive for large-file delivery. R2 credentials must remain available to generate signed download links.

---

## DEC-012: Operational Validation of Infrastructure

- **Status**: Accepted
- **Context**: Serverless infrastructure depends on external systems such as Telegram Bot API, Cloudflare Workers, GitHub Actions, R2, and Hugging Face Spaces. Source code implementation alone does not prove that those systems are deployed, connected, or receiving traffic.
- **Decision**: Treat code implementation, infrastructure deployment, and operational validation as separate project states. A milestone involving external infrastructure is not complete until live operational validation succeeds.
- **Reason**: Prevents false completion claims and keeps project state aligned with what has been verified in the real environment.
- **Impact**: `PROJECT_STATE.md`, `TODOList.md`, and deployment docs must clearly distinguish implemented code from deployed infrastructure and validated operations.

---

## DEC-013: f2 fallback for Douyin downloads

- **Status**: Accepted
- **Context**: `yt-dlp` still rejects fresh Douyin cookies with `Fresh cookies are needed`, while `f2` successfully downloads the same Douyin URL with the same exported browser cookie.
- **Decision**: Keep `yt-dlp` as the default downloader, but fall back to `f2 dy -M one` for Douyin URLs when `yt-dlp` fails.
- **Reason**: Minimal change, keeps generic downloader behavior for other platforms, and uses a Douyin-specific downloader only when needed.
- **Impact**: Workflow #1 installs `f2`; `YT_DLP_COOKIES` remains the single cookie secret and is converted to a cookie header for `f2`.

---

## DEC-014: Unified Go CLI pipeline for Telegram processing

- **Status**: Accepted
- **Context**: Telegram Workflow #2 and Workflow #3 duplicated local processing logic in Python (`ai_pipeline.py` and `render.py`). This caused divergence from local behavior, including word-level SRT being preserved as TTS chunks and `edge` being selected before Gemini.
- **Decision**: Keep Workflow #1 for ingest/R2 backup, then run the same local Go CLI pipeline in Workflow #2 using `krillinai-cli pipeline local:<video>`. Workflow #2 now performs subtitle generation, translation, TTS, blur/overlay render, R2 upload, and Telegram notification. Workflow #3 is retained for manual fallback only.
- **Reason**: Local and Telegram processing must share one implementation so future local feature changes automatically apply to CI/Telegram without manually porting Python logic.
- **Impact**: GitHub Actions runner must install Go, FFmpeg, Python dependencies, and WhisperX. Hugging Face ASR workflow is no longer the default Telegram path.

---

## DEC-015: Standardize ASR compute on GitHub Actions Go CLI

- **Status**: Accepted
- **Context**: HF Space Free Tier was considered for ASR compute to offload WhisperX from GitHub Actions. Current constraints show GitHub Actions `ubuntu-latest` public runners provide enough CPU/RAM for the present pipeline, while adding HF Space would reintroduce an external ASR microservice and risk divergence between Python/HF output and Go CLI subtitle logic.
- **Decision**: Do not use HF Space Free Tier for the default ASR compute path. Use WhisperX installed in a Python venv directly on GitHub Actions and invoke it through the Go CLI pipeline (`krillinai-cli pipeline local:<video>`).
- **Reason**:
  - GitHub Actions `ubuntu-latest` has sufficient resources for the current ASR workload.
  - Local and CI stay synchronized because ASR, subtitle normalization, translation, TTS, synchronization, and render all flow through the Go CLI.
  - Avoids adding an external ASR microservice and avoids drift between Python/HF Space output and Go pipeline behavior.
  - Debugging is simpler because ASR, translation, TTS, and render logs stay in one workflow run.
- **Impact**:
  - Workflow #2 must install FFmpeg, Python venv, WhisperX, and required Python dependencies.
  - Runtime, disk usage, and dependency install time must be monitored; dependency caching can be added later if needed.
  - HF Space is retained only as a possible future fallback, not part of the current architecture.
  - `ai_pipeline.py`, `render.py`, and HF Space ASR are legacy/manual paths, not the default Telegram pipeline.

---

_Last updated: 2026-07-07_

