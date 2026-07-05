# KrillinAI v2 — Agent Onboarding

This is the standard handoff procedure for any AI agent continuing work on KrillinAI v2.

## Mandatory Startup Procedure

Before writing or modifying any code, an AI agent **must** perform the following steps in exact order:

1. **Read `docs/PROJECT_STATE.md`** — Understand current milestone, current task, blockers, last commit, and next action.
2. **Read `docs/DECISIONS.md`** — Understand why architecture and workflows are designed this way.
3. **Read `docs/ARCHITECTURE.md`** — Understand components, pipeline, R2 layout, idempotency, and environment mapping.
4. **Read `TODOList.md`** — Work only on the current milestone/task unless the user explicitly assigned.
5. **Confirm Current Milestone** — Check the "Current Milestone" line in `PROJECT_STATE.md` and "Project Progress" in `TODOList.md`. Do not skip ahead.
6. **Execute Only Current Milestone Tasks** — Do not start Ingest, HF, Gemini, Render, or Delivery tasks unless the Current Milestone requires it.
7. **Do Not Modify Architecture** — Do not change workflow triggers, branch strategy, or environment classification without a new entry in `DECISIONS.md`.

## Completion Procedure

After finishing any work:

1. **Update `TODOList.md`** — Mark completed task checklists with `- [x]`, add to Milestone History.
2. **Update `PROJECT_STATE.md`** — Update Current Task, Next Planned Task, Blockers, Known Issues, Last Local Commit, and Last Reviewed Date.
3. **Update `DECISIONS.md`** — If a new architectural decision was made, append a new entry (ID, Title, Status, Context, Decision, Reason, Impact).
4. **Update `CHANGELOG.md`** — Follow Keep a Changelog format; add entry under "Unreleased" or new version.
5. **Run Relevant Tests** — Python `py_compile`, YAML parse, Node `--check`, secret scan, and any milestone-specific tests.
6. **Review `git diff`** — Verify no secrets, no unrelated changes, only intended modifications.
7. **Create Local Commit** — With a clear message summarizing the change.
8. **Report Result** — List files changed, tests run, commit hash, and remaining tasks.

---

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
8. `docs/CHANGELOG.md`
   - Review recent history for context.

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
- [ ] Update `docs/CHANGELOG.md` if a versioned change occurred.
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
