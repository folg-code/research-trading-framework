# Sprint 033 - Dashboard Presentation Polish

## Metadata

```text
Sprint: 033
Phase: Dashboard Application
Status: IN_PROGRESS
Planned Start: 2026-07-18
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_025, SPRINT_028 (on main)
Sprint Branch: sprint/dashboard-presentation-polish
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - apps/dashboard/docs/RUNBOOK.md
  - docs/reference/DASHBOARD_APPLICATION.md
  - SPRINT_025.md
```

---

## 0. Slice Choice

After Streamlit is on the VPS, presentation is still table-heavy: enigmatic
`run_id` labels, duplicated robustness titles, and underused analytics charts.

```text
Wave A — friendly run pickers / titles / Overview
Wave B — walk-forward charts + sweep 3D surface
Wave C — stress / Monte Carlo charts + verdict UI
```

**Out of scope:** new robustness engines, path-level Monte Carlo export (unless
a later wave explicitly dual-writes it), Live Paper redesign, HTML/`portfolio_live`.

---

## 1. Sprint Goal

```text
apps/dashboard
  -> human-readable run selection (date, model, dataset; run_id secondary)
  -> richer robustness charts from existing Parquet
  -> less raw tables / JSON dumps
```

---

## 2. MVP Scope Checklist

### Wave A

- [x] Shared run picker with human labels (created date, title, dataset/TF).
- [x] Richer robustness catalog titles from manifest `spec` (strategy template, kinds).
- [x] Overview: clearer columns (title/date first; `run_id` secondary).
- [x] `run_id` remains available in metadata / expander, not as the primary label.

### Wave B / C (later PRs)

- [x] Walk-forward IS/OOS fold charts.
- [x] Parameter sweep 3D surface from `parameter_sweep_heatmap`.
- [ ] Stress delta chart; MC percentile visualization; verdict checklist UI.

---

## 3. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S033-T001 | Shared run picker + human labels | DONE |
| S033-T002 | Richer robustness / strategy catalog titles | DONE |
| S033-T003 | Overview readability pass | DONE |
| S033-T004 | Walk-forward fold charts | DONE |
| S033-T005 | Sweep 3D surface heatmap | DONE (this PR) |
| S033-T006 | Stress / MC / verdict presentation | TODO |

---

## 4. Acceptance Criteria

1. Selectors on Market/Signal, Strategy, and Robustness pages do not lead with opaque ids.
2. Robustness titles include strategy/dataset cues when present in the manifest.
3. Existing analytics still load; no producer schema breaks required for Wave A.
4. Dashboard unit tests cover picker labels and catalog title parsing.
