# Sprint 075: Robustness Fold Geometry and Stability (Phase 18, 18D Milestone 1)

Status: **Open** — maintainer authorized opening this sprint 2026-09-22.
Goal: Implement Phase 18 18D's Milestone 1 — publish the walk-forward
window geometry already computed but dropped, plus two new derived
artifacts: `walk_forward_fold_geometry` (per-fold date ranges and
training-window overlap, read from the already-persisted but
never-read `folds/plan.json`) and `walk_forward_stability` (a
post-hoc statistical summary over the already-persisted
`walk_forward_folds.parquet`).

Sources:

- `docs/product/PRD-dashboard-robustness-research-evidence.md` (APPROVED
  2026-09-22) — Milestone 1's Goals list both new artifacts.
- `docs/planning/roadmap/PHASE_18D_WAVE0_DECISIONS.md` — D-P18D-01
  (stability statistic set), D-P18D-02 (fold-geometry table shape and
  the corrected, mode-agnostic overlap formula), both ACCEPTED
  (maintainer, 2026-09-22).
- `src/trading_framework/research/datasets/robustness.py`
  (`read_walk_forward_plan`, already reads `folds/plan.json` for
  internal use — this sprint's publisher reuses it, does not
  reimplement it).
- `apps/dashboard/src/dashboard_app/publication/evidence.py`
  (`_load_robustness_experiment`, `_ROBUSTNESS_TABLES` — the exact
  functions this sprint extends).

Architecture triage: none beyond Wave 0's own findings — D-P18D-02
already corrected the one real implementation risk (the overlap
formula's `EXPANDING`-mode failure) before this sprint started.

## Scope

In scope:

- **T001 — Publish walk-forward window geometry fields.**
  `_load_robustness_experiment`'s `raw_payload` gains `window_mode`,
  `train_duration_seconds`, `oos_duration_seconds`, `step_duration_seconds`
  read from `manifest["spec"]["walk_forward"]` — four more dict keys
  already in memory, no new read.
- **T002 — `walk_forward_fold_geometry` artifact.** New function in
  `evidence.py` (or a small new research/analytics helper, architect's
  call during implementation) that reads the experiment's
  `WalkForwardFoldPlan` via the existing
  `WalkForwardDatasetRepository.read_walk_forward_plan`, and for each
  fold emits `experiment_id`, `fold_id`, `fold_index`,
  `train_range_start`, `train_range_end`, `oos_range_start`,
  `oos_range_end`, `train_overlap_seconds_with_previous_fold` (the
  D-P18D-02 interval-intersection formula, `0` for `fold_index=0`).
- **T003 — `walk_forward_stability` artifact.** New research/analytics
  function computing D-P18D-01's five/four-statistic summary
  (`oos_net_pnl`: mean/std/min/max/pct_profitable_folds; `train_net_pnl`:
  mean/std/min/max) from the experiment's already-persisted
  `walk_forward_folds.parquet`.
- **T004 — Wire both into the publication layer; regenerate the
  committed `projection.json`.** Add both tables to
  `_ROBUSTNESS_TABLES`/the robustness sanitizer allowlist
  (`_ROBUSTNESS_EVIDENCE_TABLE_COLUMNS`), plus the four new
  `_ROBUSTNESS_EVIDENCE_ALLOWED_FIELDS` entries for the window-geometry
  fields.

Out of scope (per the PRD and Wave 0):

- **Milestone 2 (dashboard UI)** — later, after Milestone 1 exists for
  the one real experiment, per the PRD's hard sequencing gate.
- **Any new experiment kind, resimulation, or change to how folds are
  planned or executed** — per the PRD's Non-goals.
- **Backfilling or discovering additional real Robustness experiments**
  — only one exists; not this PRD's job.

## Decisions

Binding detail and rationale:
[`PHASE_18D_WAVE0_DECISIONS.md`](../roadmap/PHASE_18D_WAVE0_DECISIONS.md)
D-P18D-01/02/03, all ACCEPTED (maintainer, 2026-09-22).

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `window_mode`/duration fields published on the experiment's evidence payload | None | `apps/dashboard/src/dashboard_app/publication/evidence.py` | standard | Done | — |
| T002 | `walk_forward_fold_geometry` published, overlap formula verified against the real 24-day fold-0→1 case | None | `src/trading_framework/research/robustness/analytics/fold_stability.py` | standard | Done | — |
| T003 | `walk_forward_stability` published, verified against the real 14-fold distribution (non-degenerate) | None | `src/trading_framework/research/robustness/analytics/fold_stability.py` | standard | Done | — |
| T004 | Publication layer wired; committed `projection.json` regenerated for real | T001-T003 | `apps/dashboard/src/dashboard_app/publication/`, `apps/dashboard/publication_data/` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-074's
precedent — bundled in one PR (T001-T004 are one coherent feature).

```text
main
  └── sprint/dashboard-robustness-research-evidence-m1
        └── feat/robustness-fold-geometry-stability  (T001-T004)
```

## Acceptance criteria

- `window_mode`, `train_duration_seconds`, `oos_duration_seconds`,
  `step_duration_seconds` publish for the one real experiment, matching
  its actual manifest (45d/14d/21d).
- `walk_forward_fold_geometry` publishes all 14 real folds, with fold
  1's `train_overlap_seconds_with_previous_fold` verified equal to
  exactly 24 days by a test against the real computed value.
- `walk_forward_stability` publishes a summary that is not degenerate
  (the real 14-fold `oos_net_pnl` series is not constant).
- No new metric is computed by the dashboard at request time — every
  number traces to a Milestone 1 persisted artifact (PRD Success
  metric 4).
- Unit and dashboard suites green; `ruff check`, `ruff format --check`,
  `mypy` clean; the regenerated bundle verified against
  `pages/8_Robustness_Analysis.py` rendering with no exceptions in a
  running dashboard (Milestone 2's new sections are not yet on the
  page — only that nothing existing broke).

## Closeout

**Status: DONE.** All 4 tasks (T001-T004) implemented and verified.

**Architecture triage during implementation**: the PRD/Sprint's original
plan computed `walk_forward_fold_geometry`/`walk_forward_stability`
directly inside `apps/dashboard/src/dashboard_app/publication/evidence.py`
at publication time (mirroring 18B's `mfe_mae_pairs`). Running the full
test suite caught a real architecture-boundary violation:
`tests/unit/test_apps_boundaries.py::test_dashboard_does_not_import_forbidden_framework_packages`
(ADR-0022) forbids `apps/dashboard` from importing
`trading_framework.research` at all -- unlike Signal Research's
`mfe_mae_pairs` (a bounded copy, no derived computation), fold geometry's
overlap and stability's statistics ARE derived computations, so they
belong in the research/analytics layer, not the dashboard. Corrected by
moving both functions' computation into a new backfill script
(`scripts/robustness_research/backfill_fold_stability.py`, mirroring
18B's `backfill_adjusted_drift.py`/`backfill_context_timeline.py`
precedent exactly), which persists two new `analytics/` Parquet tables
the dashboard then reads generically like every other robustness
analytics table -- no `trading_framework` import needed in `evidence.py`
at all. Caught by the test suite before merge, not left as a static
lint-only concern.

**Implementation**:

- `src/trading_framework/research/robustness/analytics/fold_stability.py`
  (NEW) — `compute_walk_forward_fold_geometry` (D-P18D-02's
  interval-intersection overlap formula, verified correct for both
  `ROLLING` and `EXPANDING`) and `compute_walk_forward_stability`
  (D-P18D-01's mean/std/min/max/pct-profitable summary).
- `scripts/robustness_research/backfill_fold_stability.py` (NEW) — reads
  the experiment's `WalkForwardFoldPlan` and `walk_forward_folds.parquet`,
  writes both new tables. Run against the one real experiment
  (`demo-robustness-nq-half-year`); verified fold 1's overlap is exactly
  24 days and the stability summary matches D-P18D-01's real numbers
  exactly.
- `apps/dashboard/src/dashboard_app/publication/evidence.py` —
  `_ROBUSTNESS_TABLES` gained `walk_forward_fold_geometry`/
  `walk_forward_stability` (read generically, no new code path);
  `_load_robustness_experiment` now also publishes `window_mode`,
  `train_duration_seconds`, `oos_duration_seconds`, `step_duration_seconds`
  from `manifest["spec"]["walk_forward"]`.
- `apps/dashboard/src/dashboard_app/publication/sanitizers.py` —
  `_ROBUSTNESS_EVIDENCE_ALLOWED_FIELDS` gained the four window-geometry
  fields; `_ROBUSTNESS_EVIDENCE_TABLE_COLUMNS` gained allowlists for both
  new tables.
- `apps/dashboard/publication_data/projection.json` — regenerated for
  real via `scripts/dashboard/generate_public_projection.py`: 32
  artifacts (unchanged count -- no new runs, only new fields/tables on
  the existing `robustness_research_evidence` artifact), 26 projected
  inputs, 0 skipped.
- `tests/unit/research/robustness/analytics/test_fold_stability.py`
  (NEW) — 7 tests covering empty inputs, the first-fold-has-no-overlap
  case, `ROLLING` partial overlap (checked against the real 24-day
  value), `EXPANDING` full containment, no-overlap when step exceeds
  train duration, and the stability summary checked against the real
  14-fold numbers exactly.
- `apps/dashboard/tests/test_projected_research_evidence.py` — new
  `test_discovery_projects_robustness_window_geometry_and_stability`,
  covering the window-geometry fields and both new tables end to end.

**Manual verification**: started the dashboard against the regenerated
bundle and opened `8_Robustness_Analysis.py`. Page renders with no
exceptions and no server errors (Milestone 2's new sections are not yet
wired into the UI, so nothing new is visible yet -- only that nothing
existing broke).

**Tests**: unit suite **2074 passed**, dashboard suite **299 passed**
(10 in `test_projected_research_evidence.py`, up from 9 -- one new test
added), including the architecture-boundary test that caught the
mid-implementation design correction above. `ruff check`, `ruff format
--check`, `mypy` (full project-configured file set, including the new
backfill script) all clean.

**Acceptance criteria**: all met — see Manual verification and Tests
above.

**Remaining work**: Milestone 2 (dashboard UI: window geometry as
experiment assumptions, fold geometry/overlap table with disclosure
caption, stability section beside the raw per-fold view) is next, per
the PRD's sequencing gate.
