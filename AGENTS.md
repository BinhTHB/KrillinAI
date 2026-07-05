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

Khi có conflict, dùng `-X ours` để ưu tiên thay đổi từ fork hiện tại. Cờ này chỉ tự xử lý conflict theo vùng code; sau merge vẫn phải kiểm tra lại bằng `git status` và review các file liên quan.

# KrillinAI v2 - Agent Instructions

This repository follows an AI Project Operating System.

Before making ANY code changes, every AI agent MUST follow this order.

## Mandatory Startup Procedure

1. Read docs/PROJECT_STATE.md
2. Read docs/DECISIONS.md
3. Read docs/AGENT_ONBOARDING.md
4. Read docs/ARCHITECTURE.md
5. Read TODOList.md

Only after understanding the current project state may you modify code.

---

## Current Workflow

PROJECT_STATE.md

↓

DECISIONS.md

↓

ARCHITECTURE.md

↓

TODOList.md

↓

Implementation

↓

Testing

↓

Update documentation

↓

Commit

---

## Rules

- Never skip PROJECT_STATE.md.
- Never skip TODOList.md.
- Never change architecture without adding a Decision.
- Never hardcode secrets.
- Update PROJECT_STATE.md and TODOList.md after completing work.

If the user asks for project progress, report the information from PROJECT_STATE.md instead of relying only on git status.

## Work Modes

### Mode: Quick Fix

Use when:
- bug fix
- typo
- small refactor
- test fix

Required updates:
✓ CHANGELOG.md
✓ Local commit

Optional:
PROJECT_STATE.md

Do NOT update:
- DECISIONS.md
- TODOList.md
- ARCHITECTURE.md

--------------------------------

### Mode: Feature

Use when:
- implementing a TODO milestone
- adding a new module
- replacing a placeholder

Required updates:
✓ TODOList.md
✓ PROJECT_STATE.md
✓ CHANGELOG.md
✓ Local commit

Update DECISIONS.md only if an architectural decision changes.

--------------------------------

### Mode: Architecture

Use when:
- changing architecture
- changing workflow
- changing deployment strategy
- changing branch strategy

Required updates:
✓ DECISIONS.md
✓ ARCHITECTURE.md
✓ TODOList.md
✓ PROJECT_STATE.md
✓ CHANGELOG.md
✓ Local commit