# Sprint 029 — Repository Layout Foundations

## Metadata

```text
Sprint: 029
Phase: Foundation / Governance
Status: COMPLETE on main (PR #235, 2026-07-18)
Planned Start: 2026-07-18
Planned End: 2026-07-18
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 028 dashboard MVP on main (#232)
Sprint Branch: sprint/repo-layout
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
Wave 0 decisions: docs/planning/sprints/S029_WAVE0_DECISIONS.md
Architecture Sources:
  - ADR-0001 Modular Monolith
  - ADR-0002 Separate src and user_data
  - ADR-0022 Repository Top-Level Layout
  - PRB-015 architecture doc consistency
Track choice: Repo layout (A + selective B) over deep src/ domain reorg (C).
```

---

## 0. Slice Choice

After `apps/dashboard` landed, top-level reality drifted from vision §10:

```text
apps/, deploy/, demo/, local_aws_runbook/ (local), dist/ (build)
```

Agents and humans still plan against an outdated tree. This sprint freezes the
top-level layout, hardens hygiene, and wires an uv workspace — **without**
rewriting `src/trading_framework/` domain packages.

---

## 1. Sprint Goal

```text
Contributor can read ADR-0022 + MODULE_MAP + vision §10.1
  → know where apps vs framework vs deploy vs scripts live
  → uv workspace keeps root and apps/dashboard dependency versions aligned
  → generated HTML is not stored under docs/reference/
  → ops local runbooks live under deploy/ (co-located with AWS deploy)
```

---

## 2. MVP Scope Checklist

### Wave 1 — ADR + docs + hygiene

- [x] ADR-0022 Repository Top-Level Layout (ACCEPTED).
- [x] Update vision §10.1, MODULE_MAP §1–2, Developer Guide, CURRENT_STATUS.
- [x] Remove committed HTML dashboards from `docs/reference/`; point docs at demo generation.
- [x] Remove legacy `docs/architecture/` redirect after link updates.
- [x] Reinforce `.gitignore` for build/scratch artifacts (`dist/`, `.tmp_*`, demo/output).

### Wave 2 — uv workspace + apps boundary

- [x] Root uv workspace includes `apps/dashboard`.
- [x] Formalize apps import boundary (generalize D-S028-06) + architecture test.
- [x] CI runs dashboard unit tests.

### Wave 3 — ops consolidation

- [x] Document `deploy/local_aws_runbook/` as the home for local AWS smoke scripts.
- [x] Add `scripts/README.md` CLI index (no script rewrites).

---

## 3. Non-Goals / Explicit Deferrals

| Deferred | Why |
|----------|-----|
| `packages/` shared contracts | No second DTO consumer yet; keep DTOs in `dashboard_app.contracts`. |
| Deep `market_analysis/` / `research/` reorg (TD-003 / path C) | Trigger = Phase 4B orderflow or proven navigation pain. |
| Rewriting historical sprint docs | ROADMAP principle 11. |
| Microservices / K8s / feature store | Complexity Gate. |

---

## 4. PR Plan

```text
docs/repo-layout-foundation     → Wave 0 + Wave 1 + deferral notes
feat/uv-workspace-apps          → Wave 2
refactor/ops-deploy-layout      → Wave 3
```

Base: `sprint/repo-layout`. One coherent outcome per PR.
