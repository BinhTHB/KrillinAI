# KrillinAI v2 — Project State

> This file reflects the **current state of the project** and should be updated after each milestone by the agent who completes it.

---

## Project Status

- **Overall Status**: Milestone 6 (FFmpeg Render) complete; real-world visual validation pending.

- **Current Milestone**: Milestone 6 — FFmpeg Render

- **Overall Progress**: 75% (6 of 8 milestones completed)

- **Current Task**: Validate FFmpeg render output with a real 30-second subtitled video and GitHub workflow_dispatch

- **Current Branch**: `master` (development / sync upstream)

- **Production Branch**: `working-branch`

- **Last Local Commit**: `5355b66` — feat: integrate Gemini Live API TTS (gemini-3.1-flash-live-preview) via google-genai SDK

- **Last Reviewed Date**: 2026-07-06

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

- [ ] Validate Milestone 6 render pipeline

  - Run render workflow with real subtitled video assets

  - Visually inspect blur and translated subtitle overlay

  - Confirm TTS audio replaces original audio

---

## Blockers

| Blocker | Description | Impact | Mitigation |

|---------|-------------|--------|------------|

| None | None | None | None |

---

## Known Issues

| Issue | Severity | Description |

|-------|----------|-------------|

| No real R2 credentials in CI | Medium | `KRILLINAI_DRY_RUN=true` by default; integration tests blocked until credentials added |





| No Google Drive credentials | Low | Only needed for Milestone 7 (>50 MB videos) |

---

## Completed Milestones

| Milestone | Status | Completion Date |

|-----------|--------|-----------------|

| Milestone 1: Skeleton v2 | ✅ Completed | 2026-07-05 |

| Milestone 2: R2 Client | ✅ Completed | 2026-07-05 |

| Milestone 3: Ingest | ✅ Completed | 2026-07-05 |

| Milestone 4: HF Space + hf_client | ✅ Completed | 2026-07-05 |

| Milestone 5: Gemini Translation + TTS | ✅ Completed | 2026-07-05 |

| Milestone 6: FFmpeg Render | ✅ Completed | 2026-07-06 |

---

## Remaining Milestones

| Milestone | Status | Estimated Effort | Dependencies |

|-----------|--------|------------------|--------------|

| Milestone 7: Telegram + Google Drive Upload | ⏳ Not Started | ⭐⭐ Medium | Milestone 6 |

| Milestone 8: E2E Integration & Production Validation | ⏳ Not Started | ⭐⭐⭐ Hard | Milestone 7 |

| Future: Cloudflare Queue | ⏳ Not Started | ⭐⭐ Medium | Milestone 8 |

---

## Notes for Next Agent

1. **Read order**: `PROJECT_STATE.md` → `DECISIONS.md` → `AGENT_ONBOARDING.md` → `TODOList.md` → `ENVIRONMENT.md` → `DEPLOYMENT.md` → `VERSIONS.md` → `CHANGELOG.md`

2. **Current focus**: Milestone 7 (Telegram + Google Drive Upload). Before starting it, validate Milestone 6 with a real 30-second subtitled video if credentials/assets are available.

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

_Last updated: 2026-07-06_

