# Sprint 030 — Repository Navigability Hygiene

## Metadata

```text
Sprint: 030
Phase: Foundation / Governance
Status: COMPLETE on main (PR #238, 2026-07-18)
Planned Start: 2026-07-18
Planned End: 2026-07-18
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 029 (ADR-0022) on main (#235)
Sprint Branch: sprint/repo-navigability
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
Wave 0 decisions: docs/planning/sprints/S030_WAVE0_DECISIONS.md
Architecture Sources:
  - ADR-0022 Repository Top-Level Layout
Track choice: Navigability hygiene (scratch + IDE excludes + artifacts/demo) over ops/ regroup.
```

---

## 1. Sprint Goal

```text
Contributor opens the repo in the IDE
  → first-class dirs dominate the explorer
  → scratch/ holds local logs (not root .tmp_*)
  → generated demos live under artifacts/demo/
  → README map distinguishes First-class / Support / Local-only
```

---

## 2. Scope Checklist

- [x] `scratch/` + gitignore; remove leftover root `local_aws_runbook/`
- [x] `.vscode` / `.cursorignore` excludes for caches, venv, scratch, user_data
- [x] `demo/` → `artifacts/demo/` + path updates
- [x] README + Developer Guide navigation map
- [x] Amend ADR-0022 / MODULE_MAP / CURRENT_STATUS

## 3. Non-Goals

- Deep `src/` reorg, `packages/`, full `ops/` tree nesting `deploy/`
