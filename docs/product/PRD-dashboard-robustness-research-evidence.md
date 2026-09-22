# PRD — Dashboard Robustness Research Evidence Views (Phase 18, Increment 18D)

```text
Status: APPROVED (maintainer, 2026-09-22)
```

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for
`docs/product/PRD-dashboard-strategy-research-evidence.md` (18A) and
`docs/product/PRD-dashboard-signal-research-evidence.md` (18B).

Source input:
[`docs/vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md`](../vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md)
(§"Desired evidence views", the one Robustness Research row: "Rolling-window
robustness — Correctly computed persisted windows, coverage, overlap policy
and limitations; do not reuse the historical erroneous formula"), scoped to
increment **18D** only. This document is that PRD for 18D.

## Problem

Investigation, not assumption, found three things:

1. **No trace of the vision doc's "historical erroneous formula" exists
   anywhere in this repository** — not in `src/`, not in any ADR, not in
   git history (`git log --all --diff-filter=D` for any file named
   `*rolling*` returns nothing). The maintainer confirmed: treat this as a
   caution to build the feature correctly from scratch, not a bug to
   locate and fix in existing code.
2. **"Rolling window" is not a new concept in this codebase — it already
   exists inside the walk-forward mechanism (ADR-0019, Sprint 016) as
   `WalkForwardWindowMode.ROLLING`**, and the one real Robustness
   experiment on disk (`demo-robustness-nq-half-year`) already uses it:
   `train_duration_seconds=3,888,000` (45 days), `oos_duration_seconds=
   1,209,600` (14 days), `step_duration_seconds=1,814,400` (21 days).
   Because `step_duration` (21d) is smaller than `train_duration` (45d),
   **consecutive folds' train windows overlap by 24 days** — confirmed
   directly against the real persisted `folds/plan.json` (14 folds; fold 0
   trains 2025-07-14→2025-08-28, fold 1 trains 2025-08-04→2025-09-18, an
   exact 24-day overlap). This is standard rolling walk-forward technique,
   not a bug — but neither the overlap fact nor the window geometry
   (`window_mode`, the three duration fields) is ever surfaced: `evidence.py`'s
   `_load_robustness_experiment` reads `manifest["spec"]` but only extracts
   `dataset_ref`/`timeframe`/`strategy_template_id`, dropping the
   `spec["walk_forward"]` sub-object entirely, and never opens
   `folds/plan.json` (which sits at the experiment root, sibling to
   `analytics/`, and holds every fold's exact `train_range`/`oos_range`)
   at all. Today's "Walk-forward (IS/OOS)" section shows each fold's
   train/OOS net PnL bars with no disclosure that the folds share training
   data and are therefore not fully independent — a real, currently-hidden
   methodological caveat.
3. **No stability summary exists.** `walk_forward_folds.parquet` already
   persists `train_net_pnl`/`oos_net_pnl` per fold (14 real values), but no
   aggregate — mean, spread, % of folds profitable — is computed anywhere.
   A visitor sees 14 individual bars and has to eyeball consistency
   themselves.
4. **Only one real Robustness experiment exists on disk** — unlike 18A/18B,
   there is no hidden multi-run discovery gap to fix. 18D deepens the
   fidelity of the one experiment already published, it does not
   generalize across many runs.

## Goals (v1)

Two sequential milestones, matching 18A/18B's precedent.

### Milestone 1 — Research/analytics layer and publication-boundary fix

- **Publish the walk-forward window geometry already computed but
  dropped.** `window_mode`, `train_duration_seconds`, `oos_duration_seconds`,
  `step_duration_seconds` from `manifest["spec"]["walk_forward"]` — four
  more dict keys already in memory when `_load_robustness_experiment`
  reads the manifest, not a new computation.
- **New `walk_forward_fold_geometry` artifact.** One row per fold, read
  from the already-persisted `folds/plan.json` (sibling to `analytics/`,
  the same "read a raw sibling file, not `analytics/`" pattern 18B's
  `mfe_mae_pairs` established for `outcomes.parquet`): `fold_id`,
  `fold_index`, `train_range_start`, `train_range_end`, `oos_range_start`,
  `oos_range_end`, plus a derived `train_overlap_seconds_with_previous_fold`
  column (`0` for `fold_index=0`; otherwise
  `max(0, previous_fold.train_range_end - this_fold.train_range_start)`) —
  pure arithmetic over two already-persisted timestamps, the same class of
  derived fact as 18B's `shrinkage_weight` or 18A's `exposure_ratio`.
- **New `walk_forward_stability` artifact.** A one-row-per-experiment
  summary computed once, post-hoc, from the already-persisted
  `walk_forward_folds.parquet`'s `oos_net_pnl`/`train_net_pnl` columns —
  exact statistic set is this PRD's Open Question 1, not fixed here.

### Milestone 2 — Dashboard layer

- **Window geometry displayed as experiment assumptions** — `window_mode`,
  train/OOS/step durations shown alongside the existing dataset/strategy
  assumptions on `pages/8_Robustness_Analysis.py`.
- **Fold geometry and overlap table**, from the new
  `walk_forward_fold_geometry` artifact, with an explicit caption
  disclosing overlapping training windows when `step_duration_seconds <
  train_duration_seconds` — honesty about non-independence, not a
  computed "independence score" (exact wording is Open Question 2).
- **Rolling-window stability section**, from the new `walk_forward_stability`
  artifact, shown beside (never replacing) the existing per-fold
  `walk_forward_folds` table and its bar chart — the same raw-vs-derived
  pairing 18B established for `grouped_summaries` vs `adjusted_forward_drift`.

## Non-goals (v1)

- **A new `RobustnessExperimentKind.ROLLING_WINDOW` experiment type or any
  resimulation.** This PRD's rolling-window view is entirely derived from
  the *existing* walk-forward mechanism's already-computed fold plan and
  results — no new experiment kind, no new backtest run.
- **Discovering or backfilling additional real Robustness experiments.**
  Only one exists; multi-run generalization (mirroring 18A/18B's overview
  tables) is out of scope until more real experiments exist to generalize
  across.
- **Enforcing an overlap or step-vs-train ratio policy** (e.g., warning or
  rejecting a spec whose folds overlap "too much"). This PRD only
  *discloses* the geometry an experiment's author already chose; it adds
  no new validation to experiment authoring.
- **Any change to how walk-forward folds are planned or executed.** Purely
  a publication/dashboard fix over already-correct, already-running logic.

## Success metrics

1. `window_mode`, `train_duration_seconds`, `oos_duration_seconds`,
   `step_duration_seconds` are published for the one real experiment,
   verified against its actual manifest (45d/14d/21d), not assumed.
2. Every one of the real experiment's 14 folds' train/OOS date ranges is
   published, and `train_overlap_seconds_with_previous_fold` is verified
   correct for at least one real adjacent pair (fold 0 → fold 1: exactly
   24 days), checked by a test against the real computed value, not just
   "a number appears."
3. `walk_forward_stability`'s summary is computed from the real 14-value
   `oos_net_pnl` series and is verifiably not a constant (the 14 real
   folds do not all have the identical `oos_net_pnl`).
4. No new metric is computed by the dashboard at request time — every
   number traces to a Milestone 1 persisted artifact, verifiable by code
   review against ADR-0034/0035, exactly as 18A/18B required.

## Riskiest assumption

**That `folds/plan.json` is reliably persisted for every walk-forward
experiment, not just this one demo.** Checked directly against
`run_walk_forward_experiment.py`: `repo.write_walk_forward_plan(plan)` is
called exactly once, unconditionally, on every walk-forward experiment
run, and the plan is built by `plan_walk_forward_folds` before either
window mode branches — so the file is written the same way for `ROLLING`
and `EXPANDING`. `WalkForwardDatasetRepository.write_walk_forward_plan`
does raise `FileExistsError` on a re-run against the same experiment id
(the file is written once, not overwritten), which does not affect
reading it. The one remaining residual risk — an experiment predating
this write path, or one whose `folds/` directory was partially cleaned up
— is handled the same way any other missing table already is in this
codebase: an honest empty artifact, never a crash or a fabricated row.

## Constraints

- Milestone 2 does not start until Milestone 1's two new artifacts exist
  for the one real experiment — same hard sequencing gate as 18A/18B.
- No new ADR expected by default: `folds/plan.json` as a sibling-file read
  (not `analytics/`) mirrors 18B's already-accepted `outcomes.parquet`
  pattern for `mfe_mae_pairs`; the `walk_forward_stability` summary mirrors
  18B's `adjusted_forward_drift` as "a new but simple post-hoc aggregate
  over already-disclosed values." If Wave 0 finds either assumption wrong,
  that finding earns its own ADR at that point, not assumed here.
- Every Wave 0 / architect decision set goes back to the maintainer for
  explicit review before implementation starts.

## User story

As the maintainer, I want the Robustness page's already-published
walk-forward section to stop hiding the fact that its rolling-window folds
share 24 days of training data, and to show whether the strategy's
performance is actually stable across those folds or just lucky on one —
using window geometry and fold results that are already sitting on disk
and already computed correctly, not a new backtest or a new experiment
type.

## Open questions

- **Exact stability-summary statistic set for `walk_forward_stability`** —
  candidates: mean/std/coefficient-of-variation of `oos_net_pnl`, percent
  of folds with positive `oos_net_pnl`, min/max. Architect proposes,
  checked against the real 14-fold distribution rather than a guess,
  mirroring Phase 19 Wave 0's "principled starting point, explicitly
  recalibratable" precedent.
- **Overlap-disclosure wording and threshold** — is a plain "folds N and
  N+1 share X days of training data" caption sufficient, or does the
  Milestone 2 view need a per-pair numeric indicator beyond the raw
  `train_overlap_seconds_with_previous_fold` column already planned?
- **`walk_forward_fold_geometry`'s exact column set** — the shape proposed
  in Goals (fold id/index, four range timestamps, one derived overlap
  column) is a natural default, not fixed here as binding.

## Handoff

Architect: continue Wave 0 covering (a) the stability-statistic set, (b)
`walk_forward_fold_geometry`'s exact table shape, and (c) the
overlap-disclosure wording. `folds/plan.json`'s persistence guarantee is
already resolved (Riskiest assumption, above — confirmed unconditional
for both window modes). The "no new experiment kind, no resimulation" and
"one real experiment only, no multi-run generalization" scoping
decisions, and the milestone ordering (analytics before dashboard), are
already resolved — see Goals and Non-goals; do not re-litigate them.
