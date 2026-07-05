# KrillinAI v2 — Development Roadmap

> **Status**: Skeleton v2 is complete. The checklist below covers real implementations.
> **Progress marker**: `- [ ]` = pending, `- [x]` = completed.

## Project Progress

- **Current Milestone**: Milestone 3 — Ingest (yt-dlp + FFmpeg)
- **Overall Progress**: 25% (2 of 8 milestones completed)
- **Last Updated**: 2026-07-05
- **Next Recommended Task**: Replace placeholder video download/audio extraction in `scripts/v2/workflows/ingest.py`.

---

## Milestone 1: Skeleton v2

**Status**: ✅ Completed
**Estimated Effort**: ⭐⭐ Medium
**Dependencies**: None

**Target**: Establish the complete serverless skeleton: Cloudflare Worker, HF Space skeleton, 3 GitHub Actions workflows, shared modules, client placeholders, workflow orchestrators, idempotency checks, and documentation.

### Files to edit
- `worker/src/index.js`
- `worker/wrangler.toml`
- `worker/package.json`
- `hf-space/app.py`
- `hf-space/requirements.txt`
- `hf-space/Dockerfile`
- `.github/workflows/ingest.yml`
- `.github/workflows/ai_pipeline.yml`
- `.github/workflows/render.yml`
- `scripts/v2/config.py`
- `scripts/v2/logger.py`
- `scripts/v2/retry.py`
- `scripts/v2/models.py`
- `scripts/v2/layout.py`
- `scripts/v2/r2_client.py`
- `scripts/v2/telegram_client.py`
- `scripts/v2/github_client.py`
- `scripts/v2/hf_client.py`
- `scripts/v2/gemini_client.py`
- `scripts/v2/gdrive_client.py`
- `scripts/v2/workflows/ingest.py`
- `scripts/v2/workflows/ai_pipeline.py`
- `scripts/v2/workflows/render.py`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/ENVIRONMENT.md`
- `docs/VERSIONS.md`

### Tasks
- [x] Cloudflare Worker webhook + dispatch
- [x] Hugging Face Space skeleton (FastAPI + faster-whisper stub)
- [x] 3 GitHub Actions workflows (ingest, ai_pipeline, render)
- [x] Shared modules: logger, retry, models, layout
- [x] Client placeholders: R2, Telegram, GitHub, HF, Gemini, GDrive
- [x] Workflow orchestrators (ingest.py, ai_pipeline.py, render.py)
- [x] Idempotency per step (`exists()` checks)
- [x] Docs: ARCHITECTURE, DEPLOYMENT, ENVIRONMENT, VERSIONS
- [x] Environment classification (Secrets vs Variables)

### APIs / Libraries
- Cloudflare Workers / Wrangler
- Hugging Face Spaces (FastAPI + faster-whisper)
- GitHub Actions
- Python 3.10

### Definition of Done
1. All skeleton code compiles/imports without errors.
2. GitHub Actions YAML syntax is valid.
3. Worker JavaScript passes Node `--check`.
4. Documentation files created and consistent.
5. Environment variables classified correctly (Secrets vs Variables).

### Tests
- [x] Python `py_compile` on all scripts.
- [x] YAML parsing of all workflow files.
- [x] Node `--check` on Worker.
- [x] Secret scanner finds no real credentials.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 2 — R2 Client (boto3 integration)

**Status**: ✅ Completed
**Estimated Effort**: ⭐⭐ Medium
**Dependencies**: Milestone 1

**Target**: Turn the `r2_client.py` placeholder into a working S3‑compatible client backed by Cloudflare R2.

### Files to edit
- `scripts/v2/r2_client.py`
- `scripts/v2/config.py` (verify `requests` is NOT needed, only `boto3`)

### Tasks
- [x] Install `boto3` in the development environment (it is already in workflow install steps)
- [x] Add `_s3_client()` method that lazily creates a `boto3.client("s3", …)` using `CF_R2_*` env vars
- [x] Implement `exists(key)` via `head_object` (return True/False; catch `ClientError` for 404)
- [x] Implement `upload_file(local_path, key)` using `s3.upload_file`
- [x] Implement `download_file(key, local_path)` using `s3.download_file`
- [x] Remove the `# TODO: integrate boto3 …` comments
- [x] Keep `dry_run` guard so that unit tests can run without real R2

### APIs / Libraries
- **boto3** ≥ 1.28
- Cloudflare R2 (S3‑compatible API)

### Definition of Done
1. `test_r2_client.py` passes against a real (or local-mocked) R2 endpoint.
2. `exists()` returns correct True/False.
3. Upload and download round‑trip works.
4. Running `python scripts/v2/workflows/ingest.py --job-id test-1 …` with `KRILLINAI_DRY_RUN=false` uploads files to R2.

### Tests
- [x] Unit test file: `scripts/v2/tests/test_r2_client.py`
  - `test_exists_returns_false_for_missing_key`
  - `test_upload_and_download_roundtrip`
  - `test_metadata_save_and_load`
- [ ] Manual workflow_dispatch on ingest → verify R2 bucket content via Cloudflare Dashboard.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 3 — Ingest (yt-dlp + FFmpeg)

**Status**: ✅ Completed
**Estimated Effort**: ⭐⭐ Medium
**Dependencies**: Milestone 2

**Target**: Replace the placeholder video download / audio extraction with real tools.

### Files to edit
- `scripts/v2/workflows/ingest.py`
- `scripts/v2/pipeline_step.py` (already deleted; logic lives in `ingest.py`)

### Tasks
- [ ] Add `import subprocess` (already present)
- [ ] **Download video**: run `yt-dlp -o … <url>` inside `ingest.py`.
  - If `yt-dlp` is not installed, print a clear error and raise.
- [ ] **Extract audio + convert to FLAC**: run `ffmpeg -i … -vn -ac 1 -ar 16000 …`
  - Output format WAV → second pass to FLAC? Single FFmpeg pass to FLAC is sufficient: `-c:a flac -compression_level 12`
- [x] Upload raw video and FLAC audio to R2 (already wired).
- [x] If `KRILLINAI_DRY_RUN=false`, the script **must not** create placeholder files.

### APIs / Libraries
- **yt-dlp** (installed via pip in workflow steps)
- **FFmpeg** (system package, expected on runner)

### Definition of Done
1. Running `python scripts/v2/workflows/ingest.py --job-id test-1 --video-url "https://www.youtube.com/watch?v=…" --chat-id 0 --message-id 0` with `KRILLINAI_DRY_RUN=false` downloads a short YouTube clip and produces `video_orig.mp4` + `audio_orig.flac` on R2.
2. Metadata JSON exists on R2 at `jobs/test-1/metadata.json`.

### Tests
- [ ] Local test with a 10‑second public YouTube video.
- [ ] `workflow_dispatch` trigger on GitHub (dry-run first, then real).
- [ ] Verify `audio_orig.flac` plays correctly (16 kHz mono).

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 4 — Hugging Face Space + hf_client

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐⭐ Hard
**Dependencies**: Milestone 2, Milestone 3

**Target**: Deploy the HF Space Docker image and make the `hf_client.py` actually call `/transcribe` to get SRT output.

### Files to edit
- `scripts/v2/hf_client.py`
- `hf-space/app.py` (verify; should already be functional if GPU Space is deployed)

### Tasks
- [ ] **Deploy `hf-space/` to Hugging Face Spaces** as a Docker Space with GPU.
  - Ensure `Dockerfile` references the correct CUDA image.
  - Set Space secrets / env vars in HF Dashboard.
- [ ] **Test `GET /health`** returns `{"status":"ready","model":"…"}`.
- [ ] In `hf_client.py`:
  - [ ] Rewrite `check_health()` to poll `/health` until `ready` (with timeout ≈ 5 min).
  - [ ] Rewrite `transcribe(audio_path)`:
    - Send multipart POST to `{space_url}/transcribe` with `file=…`.
    - Receive SRT text back as HTTP response.
    - Return the SRT string.
- [ ] Remove dry_run guard in `hf_client.transcribe()` (it only returns placeholder now).

### APIs / Libraries
- **Hugging Face Spaces** (Docker + GPU)
- **requests** (already in requirements)

### Definition of Done
1. `python -c "from hf_client import HuggingFaceClient; hf = HuggingFaceClient(); print(hf.transcribe('test_audio.flac'))"` returns valid SRT output with word timestamps.
2. The health‑check loop exits only when the model is ready and returns within 5 min.

### Tests
- [ ] Health‑check loop test (can be simulated with placeholder).
- [ ] Transcribe integration test with a known audio file:
  - `scripts/v2/tests/test_hf_client.py`
    - `test_health_ready`
    - `test_transcribe_returns_srt`
- [ ] Manual: run `ai_pipeline.py` with a real job (dry-run first, then real).

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 5 — Gemini Translation + TTS

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐⭐ Hard
**Dependencies**: Milestone 4

**Target**: Wire up real Google Gemini API calls for SRT translation and voice synthesis.

### Files to edit
- `scripts/v2/gemini_client.py`

### Tasks
- [ ] Set up a Google Cloud project & enable Gemini API.
- [ ] Create an API key and store it in GitHub Secrets as `GEMINI_API_KEY`.
- [ ] In `gemini_client.py`:
  - [ ] `translate_srt(srt_text, target_language)`:
    - Call Gemini API with a structured prompt that preserves timecodes and only translates text content.
    - Return the translated SRT string.
  - [ ] `synthesize_voice(text, voice)`:
    - Call Gemini Voice API (gemini‑live‑tts or REST equivalent) to generate audio bytes.
    - Return raw WAV/MP3 bytes.
- [ ] Remove the `NotImplementedError` and dry_run placeholder.

### APIs / Libraries
- **Google Gemini API** (REST or Python `google‑genai` SDK)
  - Translation: `gemini-1.5-flash` (or specified via `GEMINI_MODEL`).
  - TTS: Gemini Voice (waiting for official REST) or fallback to `Edge-TTS` as alternative.

### Definition of Done
1. `translate_srt()` converts a short 5‑line Chinese SRT to Vietnamese with correct timecodes.
2. `synthesize_voice()` returns playable audio bytes.
3. When run inside `ai_pipeline.py`, the translated SRT and TTS audio appear on R2.

### Tests
- [ ] `scripts/v2/tests/test_gemini_client.py`
  - `test_translate_preserves_timecodes`
  - `test_synthesize_returns_audio`
- [ ] Integration: full `ai_pipeline.py` run with `KRILLINAI_DRY_RUN=false`.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 6 — FFmpeg Render

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐⭐⭐ Very Hard
**Dependencies**: Milestone 5

**Target**: Replace the placeholder copy in `render.py` with a real FFmpeg blur‑subtitle + overlay + audio mux pipeline.

### Files to edit
- `scripts/v2/workflows/render.py`
- Possibly `scripts/v2/render_ffmpeg.py` (new helper) if the command string becomes complex.

### Tasks
- [ ] **Original subtitle region detection** (optional for skeleton → real):
  - Strategy A: hardcode bottom‑third region (`-vf "crop=w:h:0:h-100"`).
  - Strategy B: use OCR / scene‑detect to find sub area (future enhancement).
- [ ] **Blur original subtitle**:
  ```bash
  ffmpeg -i input.mp4 \
    -vf "crop=iw:100:0:ih-100, boxblur=10:5" \
    -c:v libx264 -preset ultrafast blurred_sub_area.mp4
  ```
  → Then overlay the blurred strip back onto the original.
- [ ] **Overlay translated subtitles**:
  ```bash
  ffmpeg -i blurred_sub_area.mp4 -vf "subtitles=translated_vi.srt" output.mp4
  ```
- [ ] **Replace / mix audio** with TTS voice:
  ```bash
  ffmpeg -i video_with_sub.mp4 -i tts_voice.wav \
    -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 final.mp4
  ```
- [ ] Idempotency: if `video_final.mp4` already exists on R2, skip entirely.

### APIs / Libraries
- **FFmpeg** (system package, expected on runner).

### Definition of Done
1. Running `python scripts/v2/workflows/render.py` with real assets produces a watchable `final.mp4` where:
   - Original subtitles are blurred.
   - Translated subtitles are visible at the bottom.
   - TTS audio replaces the original audio.
2. The file is uploaded to R2.

### Tests
- [ ] Local test with a 30‑second test video containing Chinese hardcoded subs.
- [ ] `workflow_dispatch` trigger on GitHub.
- [ ] Visual inspection of the output video.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 7 — Telegram Upload + Google Drive Upload

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐ Medium
**Dependencies**: Milestone 6

**Target**: Implement real file delivery to the end user.

### Files to edit
- `scripts/v2/telegram_client.py` — `send_video()` method.
- `scripts/v2/gdrive_client.py` — `upload_file()` method.

### Tasks
- **Telegram**:
  - [ ] Implement `send_video(chat_id, video_path, caption)` using Telegram Bot API `sendVideo` (multipart/form‑data).
  - [ ] Handle files ≤ 50 MB.
  - [ ] If file > 50 MB, return a message telling the user "large file – will be delivered via Google Drive".
- **Google Drive**:
  - [ ] Parse `GOOGLE_DRIVE_CREDENTIALS` as JSON to create a `google.oauth2.service_account.Credentials` object.
  - [ ] Use `googleapiclient.discovery.build("drive", "v3", credentials=…)` to upload the file.
  - [ ] Set file permissions to `anyoneWithLink` so the link is shareable.
  - [ ] Return the public `webViewLink`.

### APIs / Libraries
- **Telegram Bot API** (native HTTP, no library needed).
- **Google APIs**: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

### Definition of Done
1. Running `telegram_client.send_video()` uploads a small video to a Telegram chat and the user can play it inline.
2. Running `gdrive_client.upload_file()` for a large file returns a public Drive link.
3. In `render.py` the end‑of‑pipeline delivery picks the correct channel automatically.

### Tests
- [ ] `test_telegram_client.py`
- [ ] `test_gdrive_client.py` (mock credentials; verify URL format).
- [ ] End‑to‑end: run `render.py` with a real job and verify the Telegram message contains the file/link.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone 8 — End-to-End Integration & Production Validation

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐⭐ Hard
**Dependencies**: Milestone 7

**Target**: Run a complete real job from Telegram → Worker → 3 workflows → Delivery, then validate stability on the `master` and `working-branch`.

### Files to edit
- Integration test scripts (new)
- No core logic changes expected; only validation.

### Tasks
- [ ] **Worker → workflow #1**: Send a real Telegram message → Worker receives webhook → dispatch `telegram_video_ingest` → Ingest runs and uploads to R2.
- [ ] **Workflow #1 → #2**: AI Pipeline triggers, transcribes, aligns, translates, generates TTS, uploads results.
- [ ] **Workflow #2 → #3**: Render triggers, produces final video, delivers via Telegram or Drive.
- [ ] **Retry test**: Delete a mid‑step R2 asset deliberately → re‑run the corresponding workflow → only the missing step should re‑execute.
- [ ] **Large video test**: Video > 50 MB → final delivery goes to Google Drive.
- [ ] **Error notification**: Inject a transient error in a workflow → Telegram receives a human‑readable error message.
- [ ] **Dry‑run → real flip**: Change `KRILLINAI_DRY_RUN` from `true` to `false` in GitHub Variables → everything continues to work.

### Environments
- [ ] `master` (dev) branch: full test suite.
- [ ] `working-branch` (prod) branch: deploy with separate Spaces / Workers.

### Definition of Done
1. A complete video job runs end‑to‑end without manual intervention.
2. The user receives the final video in Telegram within 10 minutes for a 5‑minute clip.
3. Retry works correctly.
4. The project is ready for limited production use.

### Tests
- [ ] **Full E2E test** script: `scripts/v2/tests/test_e2e.py`
  - Simulates a full pipeline run (dry‑run + real if credentials available).
- [ ] **Performance test**: Timing of each workflow relative to video length.
- [ ] **Security audit**: Re‑run secret scanner and confirm no credentials in code or logs.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Future / Backlog (Cloudflare Queue)

**Status**: ⏳ Not Started
**Estimated Effort**: ⭐⭐ Medium
**Dependencies**: Milestone 8

- [ ] Add Cloudflare Queue between Worker and Workflow #1 for traffic smoothing.
- [ ] Add Cloudflare Queue for intermediate retry (transcribe → align → translate → TTS → render).
- [ ] Automate HF Space health check & restart via GitHub Actions cron.

### Review Checklist
- [x] Code review completed
- [x] Tests passed
- [x] Documentation updated
- [x] TODOList updated
- [x] Local commit created

---

## Milestone History

| Milestone | Completion Date | Commit Hash | Summary |
|-----------|-----------------|-------------|---------|
| Milestone 1 — Skeleton v2 | 2026-07-05 | `697aeb9`, `094dcd4`, `de567cf`, `c2460d2`, `186b164`, `4e4bfca`, `a0e2420` | Built the complete v2 skeleton: Worker, HF Space skeleton, workflows, shared modules, placeholder clients, orchestration scripts, docs, version matrix, and roadmap. |
| Milestone 2 — R2 Client | 2026-07-05 | 47748dc | Implemented boto3 Cloudflare R2 client with dry-run tests, upload/download, metadata round-trip, and idempotency checks. |
| Milestone 3 — Ingest | 2026-07-05 | 18bc7e1 | Implemented video download with yt-dlp, audio extraction & conversion to FLAC with FFmpeg, and automated unit tests. |

---

_Last updated: 2026-07-05_
