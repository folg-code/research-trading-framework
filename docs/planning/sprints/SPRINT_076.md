# Sprint 076: Robustness Dashboard UI (Phase 18, 18D Milestone 2)

Status: **Open** — maintainer authorized opening this sprint 2026-09-22.
Goal: Implement Phase 18 18D's Milestone 2 — the dashboard layer over
Sprint 075's three new facts: the walk-forward window-geometry fields
(`window_mode`, train/oos/step durations), `walk_forward_fold_geometry`
(per-fold date ranges and training-window overlap) and
`walk_forward_stability` (mean/std/min/max/pct-profitable over the
already-published per-fold PnL). Milestone 1's hard sequencing gate is
satisfied — Sprint 075 is merged to `main`.

Sources:

- `docs/product/PRD-dashboard-robustness-research-evidence.md` (APPROVED
  2026-09-22) — Milestone 2's Goals list every section this sprint
  builds.
- `docs/planning/roadmap/PHASE_18D_WAVE0_DECISIONS.md` — D-P18D-03
  (overlap-disclosure wording), ACCEPTED (maintainer, 2026-09-22).
- `docs/planning/sprints/SPRINT_075.md` — this sprint's data
  prerequisite (all three new facts, real committed `projection.json`).
- `apps/dashboard/pages/8_Robustness_Analysis.py` — the exact page this
  sprint extends (unchanged existing sections: verdict, walk-forward
  fold chart, equity, parameter sweep, stress, Monte Carlo).

Architecture triage: none beyond Wave 0's own findings.

## Scope

In scope:

- **T001 — Window geometry as experiment assumptions.** Add
  `window_mode` and the three durations to the existing assumptions
  `st.write({...})` block near the top of the page, alongside dataset/
  timeframe/strategy template.
- **T002 — Fold geometry and overlap table.** New section, placed
  beside the existing "Walk-forward (IS/OOS)" fold chart/table, from
  `walk_forward_fold_geometry`. Per-fold overlap disclosure caption per
  D-P18D-03 (fraction of the fold's own training duration, no severity
  threshold).
- **T003 — Rolling-window stability section.** New section, from
  `walk_forward_stability`, shown beside (never replacing) the existing
  raw per-fold `walk_forward_folds` table/chart.
- **T004 — Honest "unavailable" handling.** Each new section shows an
  info message, not an error, when its table/field is absent (mirrors
  every other section on this page already).

Out of scope (per the PRD and Wave 0):

- **18D's own new artifacts' correctness** — already verified in
  Sprint 075 against the real experiment; this sprint only renders
  them.
- **Any new persisted artifact or backfill** — presentation-only, per
  ADR-0034/0035 (Success metric 4).

## Decisions

Binding detail and rationale:
[`PHASE_18D_WAVE0_DECISIONS.md`](../roadmap/PHASE_18D_WAVE0_DECISIONS.md)
D-P18D-03, ACCEPTED (maintainer, 2026-09-22).

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Window geometry fields shown in experiment assumptions | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Open | — |
| T002 | Fold geometry/overlap table with D-P18D-03 disclosure caption | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Open | — |
| T003 | Stability section beside the raw per-fold view | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Open | — |
| T004 | Honest "unavailable" messaging verified for all three new sections | T001-T003 | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Open | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-075's
precedent — bundled in one PR (T001-T004 are one coherent UI feature).

```text
main
  └── sprint/dashboard-robustness-research-evidence-m2
        └── feat/robustness-dashboard-ui  (T001-T004)
```

## Acceptance criteria

- Window geometry, fold overlap and stability summary all render for
  the one real experiment with real numbers (45d/14d/21d train/oos/step;
  24-day overlap on fold 1; the real 14-fold stability summary).
- Overlap disclosure is per-fold, phrased as a fraction of the fold's
  own training duration, no severity threshold (D-P18D-03).
- No new metric is computed by the dashboard at request time.
- Dashboard suite green; `ruff check`, `ruff format --check`, `mypy`
  clean; page verified rendering against the real committed bundle in a
  running dashboard, no exceptions.

## Closeout

_Pending implementation._
