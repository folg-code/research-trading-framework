# Phase 18 (Increment 18D) — Wave 0 Decisions

```text
Status: ACCEPTED (maintainer, 2026-09-22)
Basis:  docs/product/PRD-dashboard-robustness-research-evidence.md (APPROVED)
        src/trading_framework/research/robustness/walk_forward.py as on main
        src/trading_framework/research/datasets/robustness.py as on main
        src/trading_framework/application/robustness_research/run_walk_forward_experiment.py as on main
        user_data/research/strategy_robustness/experiments/demo-robustness-nq-half-year/*
          on disk (the one real experiment: folds/plan.json, 14 folds;
          analytics/walk_forward_folds.parquet, 14 rows)
```

Architecture triage investigated all three of the PRD's Open Questions
directly against the codebase and the one real experiment's actual
persisted data, rather than treating them as open design questions to
answer from first principles — the same discipline 18A/18B's Wave 0
applied.

---

## D-P18D-01 — `walk_forward_stability`'s statistic set

### Problem statement

The PRD proposed candidates (mean/std/coefficient-of-variation of
`oos_net_pnl`, percent of profitable folds, min/max) without checking
them against real numbers.

### Decision

**Mean, standard deviation, min, max and percent-profitable of
`oos_net_pnl`, computed once from the real 14 folds — coefficient of
variation is dropped:**

```text
oos_net_pnl_mean = 9.70
oos_net_pnl_std  = 320.31   (sample standard deviation, ddof=1 -- one
                             estimator, documented, matching this
                             project's existing rule against an
                             undocumented statistic choice)
oos_net_pnl_min  = -511.25
oos_net_pnl_max  = 549.25
pct_profitable_folds = 0.50   (7 of 14 folds)
```

`train_net_pnl` gets the same four descriptive statistics (mean, std,
min, max — no `pct_profitable`, since training-window profitability is
not itself decision-relevant the way OOS profitability is) for
symmetry, at zero extra cost (the column is already read alongside
`oos_net_pnl`).

### Reasoning

- **Coefficient of variation was checked against the real numbers and
  found actively misleading, not merely unnecessary**: `std / mean =
  320.31 / 9.70 ≈ 33`, a huge, sign-flipping ratio that means nothing
  when the mean straddles zero — exactly the class of statistic this
  project's own precedent (Phase 19 Wave 0, Signal Research's shrinkage
  formula) rejects once checked against real data rather than assumed
  sound in the abstract.
- Mean/std/min/max/pct-profitable are all well-defined regardless of the
  mean's sign or magnitude, and directly answer the PRD's own framing
  ("is performance actually stable across folds, or lucky on one") —
  a near-zero mean with high std and exactly half the folds profitable
  is itself the honest answer for this one real experiment, not a
  degenerate result to explain away.
- No new schema-version/versioning field, matching the existing
  `walk_forward_folds`/`walk_forward_equity` tables' own convention
  (`experiment_id` only, no `schema_version` column) — Robustness
  Research's existing persisted tables never adopted Signal Research's
  newer `schema_version`-per-row convention, and this PRD does not import
  it unilaterally into one new table while leaving the other four
  untouched.

### Alternatives considered

- **Coefficient of variation, as originally proposed.** Rejected after
  checking the real numbers — see Reasoning above.
- **A Sharpe-like ratio of fold returns** (mean / std, the reciprocal of
  CV). Rejected for the same near-zero-mean reason as CV; additionally,
  nothing in this codebase computes a Sharpe ratio over a 14-point
  sample of fold-level PnL, and inventing one here would be exactly the
  kind of new, unreviewed metric ADR-0034/0035 warns against.
- **Median instead of mean.** Not rejected outright, but not added
  either — mean is already the convention every other summary artifact
  in this codebase uses (`summary_metrics.forward_return_mean`,
  `distribution_summaries`), and adding median without a stated need
  would be scope creep, not a stability requirement the PRD names.

---

## D-P18D-02 — `walk_forward_fold_geometry`'s exact table shape and overlap formula

### Problem statement

The PRD proposed `train_overlap_seconds_with_previous_fold =
max(0, previous_train_end - this_train_start)`. This formula is only
correct for `ROLLING` mode where the train window slides forward by a
fixed step smaller than its duration. It was not checked against
`EXPANDING` mode, where the train window's start is anchored and only
its end grows each fold — under the PRD's original formula, an
`EXPANDING` fold's overlap would still compute as
`previous_train_end - this_train_start`, which for a fixed `train_start`
across all folds equals a nonsensical negative number
(`this_train_start` never changes, so the subtraction produces the
*full* previous fold duration with the wrong sign once `this_train_start
< previous_train_end`, rather than correctly reporting full containment).

### Decision

**Redefine the overlap as a proper interval intersection, correct for
both window modes:**

```text
overlap_seconds = max(0,
    min(previous.train_range_end, this.train_range_end)
    - max(previous.train_range_start, this.train_range_start)
)
```

`0` for `fold_index = 0` (no previous fold). Column renamed
`train_overlap_seconds_with_previous_fold` unchanged in name, but the
formula above replaces the PRD's draft one.

`walk_forward_fold_geometry`'s final column set, read from
`folds/plan.json` (joined by `fold_index`) with no `schema_version`
column (matching D-P18D-01's reasoning):

```text
experiment_id, fold_id, fold_index,
train_range_start, train_range_end,
oos_range_start, oos_range_end,
train_overlap_seconds_with_previous_fold
```

Verified against the real 14 folds: fold 0's `train_overlap_seconds_with_previous_fold
= 0` (no previous fold); fold 1's `= 2,073,600` seconds (24 days) exactly
— `min(2025-08-28, 2025-09-18) - max(2025-07-14, 2025-08-04) =
2025-08-28 - 2025-08-04 = 24 days`, matching the PRD's own hand
computation.

### Reasoning

- The interval-intersection formula is the standard, symmetric way to
  compute overlap between two ranges and degrades correctly to `0` for
  genuinely non-overlapping folds (any `ROLLING` schedule where
  `step_duration >= train_duration`) without a mode-specific branch in
  the dashboard or the publisher — one formula, both modes, checked
  against the one real (`ROLLING`) experiment's actual numbers.
- No `EXPANDING`-mode real experiment exists on disk to check the
  full-containment case directly, so this decision documents the
  *formula's* correctness by construction (interval intersection is
  mode-agnostic) rather than claiming a second real-data verification
  that isn't possible yet — an honest limitation, not a fabricated
  check.
- Matches 18B's `mfe_mae_pairs` precedent exactly: a sibling raw file
  outside `analytics/` (`folds/plan.json`, sibling to `analytics/`, same
  as `outcomes.parquet`), read once, joined to an already-persisted
  table (`walk_forward_folds`) by a shared key (`fold_index`), with one
  small derived column — not a new experiment kind, not a resimulation.

### Alternatives considered

- **The PRD's original `previous_train_end - this_train_start` formula.**
  Rejected — incorrect for `EXPANDING` mode, as shown above.
- **A boolean `overlaps_previous_fold` flag instead of a duration.**
  Rejected — throws away the magnitude (`24 days` out of `45 days`
  training duration is a materially different disclosure than `1 day`
  out of `45`), and the PRD's own Success metric 2 requires a checkable
  numeric value, not a flag.

---

## D-P18D-03 — Overlap-disclosure wording

### Problem statement

The PRD left the exact caption wording as an open question, proposing
"folds N and N+1 share X days of training data" as a plausible default.

### Decision

**Confirmed as the default wording, generalized to state the fraction
of the current fold's training window that overlaps, and phrased
per-fold rather than per-pair (matching how the geometry table's own
row is per-fold, not per-pair):**

```text
"This fold's training window overlaps the previous fold's training
window by {overlap_days} of its own {train_duration_days} days --
overlapping folds are not fully independent evidence."
```

For `fold_index = 0`: `"First fold -- no previous training window to
compare."` For a fold whose `train_overlap_seconds_with_previous_fold =
0`: `"No overlap with the previous fold's training window."` No
numeric threshold triggers a warning-level caption versus an
info-level one — every fold's overlap is disclosed identically,
regardless of magnitude, per the PRD's own Non-goal ("this PRD only
discloses the geometry ... it adds no new validation").

### Reasoning

- Per-fold phrasing (not per-pair) lets the wording live directly next
  to `walk_forward_fold_geometry`'s own per-fold row in the Milestone 2
  table, with no separate pairing/lookup structure needed in the
  dashboard.
- Expressing the overlap as a fraction of the fold's own training
  duration (`24 of 45 days`), not just the absolute day count, answers
  the PRD's User story directly — a visitor can immediately judge "over
  half this fold's training data was also used by the previous fold,"
  which a bare "24 days" cannot convey without also knowing the
  training window's total length.
- No severity threshold (info vs. warning) avoids inventing an
  unreviewed "how much overlap is too much" policy — exactly the kind
  of validation the PRD's Non-goals explicitly excludes.

### Alternatives considered

- **A single per-experiment "average overlap" summary instead of
  per-fold captions.** Rejected — collapses exactly the fold-by-fold
  detail the PRD's Problem section says is missing today; an average
  would hide that fold 1 overlaps 24 of 45 days while a hypothetical
  fold with `step_duration >= train_duration` would show `0`.
- **A warning icon or color threshold above some overlap percentage.**
  Rejected — introduces an unreviewed judgment call about what counts
  as "too much" overlap, which the PRD's Non-goals section explicitly
  keeps out of this increment.

---

## Summary for maintainer review

| Decision | Recommendation | Status |
|---|---|---|
| D-P18D-01 | `walk_forward_stability`: mean/std/min/max/pct-profitable of `oos_net_pnl` (+ mean/std/min/max of `train_net_pnl`); coefficient of variation dropped after checking the real near-zero-mean numbers | ACCEPTED (maintainer, 2026-09-22) |
| D-P18D-02 | `walk_forward_fold_geometry` table shape fixed; overlap redefined as interval intersection (mode-agnostic, correct for both `ROLLING` and `EXPANDING`) | ACCEPTED (maintainer, 2026-09-22) |
| D-P18D-03 | Overlap-disclosure caption: per-fold, phrased as a fraction of the fold's own training duration, no severity threshold | ACCEPTED (maintainer, 2026-09-22) |

All three decisions above are Accepted (maintainer, 2026-09-22). Per this
project's governance convention, architecture triage investigated and
recommended; the maintainer's explicit review and acceptance make them
binding on implementation from this point forward.
