# KrillinAI v2 — Project State

> This file reflects the **current state of the project** and should be updated after each milestone by the agent who completes it.

---

## Project Status

- **Overall Status**: Milestone 2 (R2 Client) complete. Ready for Milestone 3 (Ingest).
- **Current Milestone**: Milestone 3 — Ingest (yt-dlp + FFmpeg)
- **Overall Progress**: 25% (2 of 8 milestones completed)
- **Current Task**: Implement real video download and audio extraction in `scripts/v2/workflows/ingest.py`
- **Current Branch**: `master` (development / sync upstream)
- **Production Branch**: `working-branch`
- **Last Local Commit**: `3487e39` — feat: implement boto3 R2 client and add dry-run tests for Milestone 2
- **Last Reviewed Date**: 2026-07-05
- **Last Updated By**: AI Agent (factory-droid)

---

## Current Environment

### Development Environment
- **Branch**: `master`
- **Trigger**: `repository_dispatch` (development webhook) or manual `workflow_dispatch`.
- **Target Cloudflare Worker**: configured on local development/dev wrangler namespace (e.g. `krillin-ai-dev`).
- **Target Hugging Face Space**: `krillin-asr-dev` via variable `HF_SPACE_URL`.
- **Target R2 Bucket**: dev bucket configured via variable `CF_R2_BUCKET`.

### Production Environment
- **Branch**: `working-branch`
- **Trigger**: `repository_dispatch` (production webhook).
- **Target Cloudflare Worker**: configured on prod wrangler namespace (e.g. `krillin-ai-prod`).
- **Target Hugging Face Space**: `krillin-asr-prod` via variable `HF_SPACE_URL`.
- **Target R2 Bucket**: prod bucket configured via variable `CF_R2_BUCKET`.

---

## Deployment Status

- **Development Deployment**: 🚧 In Progress (Skeleton deployed; API integrations pending)
- **Production Deployment**: ⏳ Not Started (Waiting for dev validation)

---

## Next Planned Task

- [ ] Start Milestone 3: Implement ingest (`scripts/v2/workflows/ingest.py`)
  - Download video with `yt-dlp`
  - Extract FLAC audio with `FFmpeg`
  - Upload raw video and audio to R2
  - Keep `dry_run` guard for testing

---

## Blockers

| Blocker | Description | Impact | Mitigation |
|---------|-------------|--------|------------|
| Manual R2 integration not verified | R2 credentials are configured in GitHub, but real workflow upload/download still needs validation | Cannot confirm real R2 round-trip in CI yet | Run ingest workflow after Milestone 3 implementation |

---

## Known Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| No real R2 credentials in CI | Medium | `KRILLINAI_DRY_RUN=true` by default; integration tests blocked until credentials added |
| No HF Space deployed | Medium | `HF_SPACE_URL` variable must point to a deployed Space for Milestone 4 |
| No Gemini API key | Medium | `GEMINI_API_KEY` secret required for Milestone 5 |
| No Google Drive credentials | Low | Only needed for Milestone 7 (>50 MB videos) |

---

## Completed Milestones

| Milestone | Status | Completion Date |
|-----------|--------|-----------------|
| Milestone 1: Skeleton v2 | ✅ Completed | 2026-07-05 |
| Milestone 2: R2 Client | ✅ Completed | 2026-07-05 |

---

## Remaining Milestones

| Milestone | Status | Estimated Effort | Dependencies |
|-----------|--------|------------------|--------------|
| Milestone 3: Ingest | ⏳ Not Started | ⭐⭐ Medium | Milestone 2 |
| Milestone 4: HF Space + hf_client | ⏳ Not Started | ⭐⭐⭐ Hard | Milestone 2, 3 |
| Milestone 5: Gemini Translation + TTS | ⏳ Not Started | ⭐⭐⭐ Hard | Milestone 4 |
| Milestone 6: FFmpeg Render | ⏳ Not Started | ⭐⭐⭐⭐ Very Hard | Milestone 5 |
| Milestone 7: Telegram + Google Drive Upload | ⏳ Not Started | ⭐⭐ Medium | Milestone 6 |
| Milestone 8: E2E Integration & Production Validation | ⏳ Not Started | ⭐⭐⭐ Hard | Milestone 7 |
| Future: Cloudflare Queue | ⏳ Not Started | ⭐⭐ Medium | Milestone 8 |

---

## Notes for Next Agent

1. **Read order**: `PROJECT_STATE.md` → `DECISIONS.md` → `AGENT_ONBOARDING.md` → `TODOList.md` → `ENVIRONMENT.md` → `DEPLOYMENT.md` → `VERSIONS.md` → `CHANGELOG.md`
2. **Current focus**: Milestone 3 (Ingest). Implement `yt-dlp` download and `FFmpeg` audio extraction in `scripts/v2/workflows/ingest.py`.
3. **Do not** change architecture, workflow triggers, or branch strategy without a new entry in `DECISIONS.md`.
4. **Secrets/Variables**: Never hardcode. Use `config.py` → environment variables → GitHub Secrets/Variables.
5. **After finishing a task**:
   - Update `TODOList.md` (mark `- [x]`).
   - Update this `PROJECT_STATE.md` (Current Task, Next Planned Task, Last Local Commit).
   - If a new architectural decision was made, add to `DECISIONS.md`.
   - Update `CHANGELOG.md` following Keep a Changelog.
   - Create a local commit with a clear message.
   - Report summary to user.

---

_Last updated: 2026-07-05_

