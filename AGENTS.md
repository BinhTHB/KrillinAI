# Hướng dẫn upstream dự án gốc KrillinAI

Tài liệu này hướng dẫn cách đồng bộ thay đổi từ repository gốc KrillinAI vào fork hiện tại.

## Remote đang dùng

- Fork hiện tại: `origin` -> `https://github.com/BinhTHB/KrillinAI.git`
- Dự án gốc: `upstream` -> `https://github.com/krillinai/KrillinAI.git`
- Nhánh phát triển chính của fork: `master`

## Quy trình đồng bộ upstream

Thực hiện trên nhánh `master` của fork:

```bash
git checkout master
git fetch upstream
git merge upstream/master -X ours -m "merge: merge upstream/master into master, preferring current fork changes on conflict"
git status
git push origin master
```

Khi có conflict, dùng `-X ours` để ưu tiên thay đổi từ fork hiện tại. Sau merge luôn kiểm tra lại bằng `git status` và review các file liên quan.

---

# KrillinAI v2 - Agent Instructions

This repository follows an AI Project Operating System (AI-POS).

Every AI agent MUST follow this document.

Failure to follow this workflow means the task is **NOT COMPLETE**.

---

# Mandatory Startup Procedure

Before making ANY code changes:

1. Read `docs/PROJECT_STATE.md`
2. Read `docs/DECISIONS.md`
3. Read `docs/AGENT_ONBOARDING.md`
4. Read `docs/ARCHITECTURE.md`
5. Read `TODOList.md`

Only after understanding the current project state may implementation begin.

Never skip these documents.

---

# Standard Workflow

Every implementation MUST follow this sequence.

```
Read Project State

↓

Implementation

↓

Testing

↓

POS Synchronization

↓

POS Validation

↓

Commit (if requested)

↓

Final Report
```

Do not skip any stage.

---

# Project Work Modes

## Mode: Quick Fix

Use for:

- Bug fix
- Typo
- Small refactor
- Test fix

Required:

- CHANGELOG.md

Optional:

- PROJECT_STATE.md

Do NOT modify unless necessary:

- TODOList.md
- DECISIONS.md
- ARCHITECTURE.md

---

## Mode: Feature

Use for:

- Implementing a milestone
- New module
- Replacing placeholder implementation
- New workflow

Required:

- TODOList.md
- PROJECT_STATE.md
- CHANGELOG.md

Update only if applicable:

- DECISIONS.md
- DEPLOYMENT.md
- ENVIRONMENT.md
- VERSIONS.md
- ARCHITECTURE.md

---

## Mode: Architecture

Use for:

- Architecture changes
- Deployment changes
- Workflow changes
- Infrastructure changes
- Branch strategy changes

Required:

- DECISIONS.md
- ARCHITECTURE.md
- PROJECT_STATE.md
- TODOList.md
- CHANGELOG.md
- DEPLOYMENT.md
- ENVIRONMENT.md
- VERSIONS.md

---

# Mandatory POS Synchronization

After every completed task, the agent MUST synchronize the AI-POS.

Always update:

- PROJECT_STATE.md
- TODOList.md

Update when applicable:

- DECISIONS.md
- CHANGELOG.md
- ARCHITECTURE.md
- DEPLOYMENT.md
- ENVIRONMENT.md
- VERSIONS.md

Do not silently skip document updates.

If a document is not updated, explain why.

---

# POS Validation Checklist

Before reporting completion, verify:

□ PROJECT_STATE.md reflects current implementation.

□ TODOList.md reflects completed work.

□ CHANGELOG.md records user-visible changes.

□ DECISIONS.md updated if any technical decision changed.

□ ARCHITECTURE.md updated if architecture changed.

□ DEPLOYMENT.md updated if deployment changed.

□ ENVIRONMENT.md updated if environment variables, secrets or infrastructure changed.

□ VERSIONS.md updated if dependency/runtime/model versions changed.

---

# Definition of Done

A task is NOT COMPLETE until ALL applicable conditions are satisfied.

Required:

□ Implementation finished.

□ Code builds successfully (when applicable).

□ Tests executed OR explicitly state why tests were not executed.

□ PROJECT_STATE.md synchronized.

□ TODOList.md synchronized.

□ Relevant documentation synchronized.

□ Remaining work documented.

---

# Final Report Template

Every implementation MUST end with the following report.

```
Implementation Summary
- ...

Files Changed
- ...

Tests
- Executed:
- Result:

POS Synchronization

PROJECT_STATE.md
- Updated / Not applicable (reason)

TODOList.md
- Updated / Not applicable (reason)

CHANGELOG.md
- Updated / Not applicable (reason)

DECISIONS.md
- Updated / Not applicable (reason)

ARCHITECTURE.md
- Updated / Not applicable (reason)

DEPLOYMENT.md
- Updated / Not applicable (reason)

ENVIRONMENT.md
- Updated / Not applicable (reason)

VERSIONS.md
- Updated / Not applicable (reason)

Remaining Risks
- ...

Next Recommended Task
- ...
```

No section may be omitted.

---

# Project Closeout Procedure

Before declaring the task complete, execute:

1. Run tests (or explain why not).
2. Synchronize all applicable POS documents.
3. Validate POS consistency.
4. Produce the mandatory Final Report.
5. Wait for user review.

Only after completing all five steps is the task considered complete.

---

# General Rules

- Never skip PROJECT_STATE.md.
- Never skip TODOList.md.
- Never hardcode secrets.
- Never change architecture without recording a Decision.
- Never modify deployment without updating DEPLOYMENT.md.
- Never modify environment configuration without updating ENVIRONMENT.md.
- Never change dependency or runtime versions without updating VERSIONS.md.
- If user asks for project progress, answer using PROJECT_STATE.md instead of relying on Git status.
- Documentation is part of the implementation, not an optional follow-up.

# Agent Self-Review

Before responding to the user, ask yourself:

- Did I update every affected POS document?
- Is PROJECT_STATE consistent with TODOList?
- Does DECISIONS reflect any new technical choices?
- Can another AI continue the project tomorrow without reading chat history?

If any answer is "No", continue working before responding.