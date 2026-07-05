# KrillinAI v2 — Agent Onboarding

This is the standard handoff procedure for any AI agent continuing work on KrillinAI v2.

## Required Read Order

1. `docs/PROJECT_STATE.md`
   - Understand current milestone, current task, blockers, last commit, and next action.
2. `docs/DECISIONS.md`
   - Understand why architecture and workflows are designed this way.
3. `docs/ARCHITECTURE.md`
   - Understand components, pipeline, R2 layout, idempotency, and environment mapping.
4. `TODOList.md`
   - Work only on the current milestone/task unless the user explicitly changes priority.
5. `docs/ENVIRONMENT.md`
   - Verify correct Secrets vs Variables classification.
6. `docs/DEPLOYMENT.md`
   - Follow deployment and environment mapping rules.
7. `docs/VERSIONS.md`
   - Check pinned/recommended versions before installing/upgrading dependencies.

## Standard Working Procedure

1. Run `git status` and inspect the working tree before changes.
2. Read the current milestone in `TODOList.md`.
3. Implement only the requested task or next planned task.
4. Do not change the overall architecture unless the user explicitly requests it.
5. If a new architectural decision is required:
   - add a new entry to `docs/DECISIONS.md`;
   - include Context, Decision, Reason, Impact.
6. Never add real secrets to the repository.
7. Do not add `.env` files.
8. Keep environment configuration in GitHub/Cloudflare/Hugging Face variables and secrets.
9. Preserve `master` as development / upstream sync branch.
10. Preserve `working-branch` as production branch.

## Completion Checklist for Any Task

Before reporting completion:

- [ ] Update `TODOList.md` checklist items.
- [ ] Update `docs/PROJECT_STATE.md` current task, next planned task, blockers, known issues, and last commit placeholder.
- [ ] Update `docs/DECISIONS.md` if a new architecture decision was made.
- [ ] Run relevant tests/checks.
- [ ] Review `git diff` for accidental secrets or unrelated changes.
- [ ] Create a local git commit.
- [ ] Report files changed, tests run, commit hash, and remaining TODOs.

## Rules for Milestone Work

- Milestone 2 starts with R2 Client implementation.
- Do not jump to Ingest, HF, Gemini, Render, or Delivery until prerequisites are complete unless the user explicitly asks.
- Keep each milestone independently testable.
- Mark completed tasks with `- [x]`; never delete completed tasks from `TODOList.md`.

## If You Are Unsure

Stop and inspect:

1. `docs/PROJECT_STATE.md`
2. `TODOList.md`
3. `docs/DECISIONS.md`

If still unclear, ask the user using a structured clarification question.
