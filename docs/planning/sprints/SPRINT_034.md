# Sprint 034 - Public Dashboard Demo Polish

## Metadata

```text
Sprint: 034
Phase: Dashboard Application
Status: COMPLETE
Planned Start: 2026-07-18
Planned End: 2026-07-18
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_033 (on main)
Sprint Branch: sprint/dashboard-public-demo-polish
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - apps/dashboard/docs/RUNBOOK.md
  - docs/reference/DASHBOARD_APPLICATION.md
  - Desktop brief: Zmiany w publicznym demo Trading Research Framework
```

---

## 0. Slice Choice

Public dashboard must look like a polished product demo for recruiters, not an
internal developer tool.

```text
Wave 1 — Public shell (homepage, nav rename, diagnostics expander)
Wave 2 — Research Catalog filters + human columns
Wave 3 — Strategy Research KPI / equity / trade presentation
Wave 4 — Robustness verdict / WF / heatmap-first / stress / MC
Wave 5 — Live Paper Trading status / KPI / chart / position
```

**Out of scope:** new research engines, path-level Monte Carlo spaghetti,
separate admin app, model overlays without data in storage.

---

## 1. Sprint Goal

```text
apps/dashboard
  -> Project Overview + clean public navigation
  -> no public editing of storage / status URL
  -> readable catalog, strategy, robustness, live paper presentation
```

---

## 2. Decisions

- Diagnostics: collapsed **System diagnostics**; no editable inputs when
  `DASHBOARD_STORAGE_ROOT` comes from env (VPS).
- PnL unit label: **pts** for current NQ demo unless run metadata says otherwise.
- Parameter sweep: default **2D heatmap**; 3D surface optional.

---

## 3. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S034-T001 | Sprint branch + this plan | DONE |
| S034-T002 | Public shell (home, nav, diagnostics) | DONE |
| S034-T003 | Research Catalog filters + columns | DONE |
| S034-T004 | Strategy presentation | DONE |
| S034-T005 | Robustness presentation | DONE |
| S034-T006 | Live Paper presentation | DONE |
| S034-T007 | Closure + integrate to main | DONE (this PR) |

---

## 4. Acceptance Criteria

1. Public home matches demo brief (no MVP/DuckDB/storage path on main view).
2. Sidebar nav uses Project Overview / Research Catalog / Market & Signal /
   Strategy / Robustness Analysis / Live Paper Trading.
3. Public users cannot change storage root or status URL when env is set.
4. Catalog filters work; technical IDs live under Technical details.
5. Strategy / Robustness / Live pages meet wave checklists without inventing data.
6. Dashboard unit tests cover new helpers and chrome behaviour.
