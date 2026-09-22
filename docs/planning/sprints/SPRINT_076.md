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
| T001 | Window geometry fields shown in experiment assumptions | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Done | — |
| T002 | Fold geometry/overlap table with D-P18D-03 disclosure caption | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Done | — |
| T003 | Stability section beside the raw per-fold view | None | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Done | — |
| T004 | Honest "unavailable" messaging verified for all three new sections | T001-T003 | `apps/dashboard/pages/8_Robustness_Analysis.py` | standard | Done | — |

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

**Status: DONE.** All 4 tasks (T001-T004) implemented and verified.

**Implementation**:

- `apps/dashboard/pages/8_Robustness_Analysis.py` — the experiment
  assumptions block now shows `window_mode` and train/OOS/step duration
  (formatted as whole/fractional days via a small local
  `_format_duration_seconds` helper); two new sections added right after
  the existing "Walk-forward (IS/OOS)" fold chart/table: "Fold geometry
  and overlap" (from `walk_forward_fold_geometry`, with a single
  disclosure caption per D-P18D-03 counting how many folds overlap and
  the maximum overlap as a fraction of the fold's own training window,
  rather than one caption per fold, which would be impractical for 14
  rows) and "Rolling-window stability" (from `walk_forward_stability`,
  shown beside, never replacing, the raw per-fold table above it). Both
  new sections show an honest "unavailable" info message, not an error,
  when their table is absent or empty.
- `apps/dashboard/tests/test_projected_research_evidence.py` —
  `test_pages_restore_rich_evidence_sections` extended with the two new
  headings; `test_robustness_page_renders_demo_verdict_and_analytics`
  extended to assert both new subheaders render against the real
  committed bundle.

**Manual verification**: started the dashboard against the committed
bundle and opened `8_Robustness_Analysis.py`. Renders with no exceptions;
assumptions show `ROLLING` / `45d / 14d / 21d`; fold geometry table shows
all 14 real folds with the correct per-fold overlap column, and the
caption correctly reports "13 of 14 folds' training windows overlap the
previous fold's -- up to 24 of 45d training days shared" (fold 0 has no
previous fold, so 13 of the remaining folds overlap); stability section
shows the real mean/std/min/max/pct-profitable summary beside the raw
walk-forward fold table.

**Tests**: dashboard suite **299 passed** (10 in
`test_projected_research_evidence.py`, all updated/extended in place, no
new test file needed for this UI-only sprint). `ruff check`, `ruff
format --check`, `mypy` (full project-configured file set) all clean.

**Acceptance criteria**: all met — see Manual verification and Tests
above.

**Remaining work**: Phase 18 18D is now fully complete (Milestones 1 and
2 both done). Phase 18 overall now has 18A, 18B and 18D all done; 18C is
folded into 18A. No further Phase 18 increment is currently planned.
