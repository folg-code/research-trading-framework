# PRD — Dashboard Signal Research Evidence Views (Phase 18, Increment 18B)

```text
Status: APPROVED (maintainer, 2026-09-18)
```

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11/12/13,
the ML runtime-promotion track and
`docs/product/PRD-dashboard-strategy-research-evidence.md` (18A).

Source input:
[`docs/vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md`](../vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md)
(§"Desired evidence views", Market and Signal Research rows), scoped to
increment **18B** only (18D remains a separate, later PRD). This document
is that PRD for 18B.

## Problem

`apps/dashboard/pages/4_Market_and_Signal_Research.py` already has a
per-run selector and reads `summary_metrics`, `grouped_summaries`,
`distribution_summaries`, `conditional_comparison`, `metric_histograms`,
`quality_warnings` and `join_diagnostics` — materially richer than 18A's
pre-Sprint-071 baseline was. Investigation found two problems, one a
genuine data-completeness bug, one a scope gap against the vision doc:

1. **Root mismatch (real bug, not a scope gap).** The real Signal
   Research data lives under `user_data/research/market_research/runs/`
   (6 runs). `catalog.scanner.list_runs`'s `market_research_runs_dir`
   resolves under whichever `storage_root` it is called with; the
   dashboard's generic catalog discovery
   (`discover_catalog_inputs`, called with `--storage-root
   user_data/workspace`) never finds this directory — `user_data/workspace`
   has no `research/market_research/` at all. The Research Catalog page
   shows **"Signal: 0"** as a direct consequence. Separately, only 3 of
   the 6 real runs have an `analytics/` folder (the format
   `discover_research_evidence_inputs` requires); the other 3 (newer,
   2026-09-15, `schema_version: signal_research.v2` with
   `context.parquet`/`occurrences.parquet`/`outcomes.parquet` at the run
   root) are silently skipped — confirmed directly as the "3 skipped"
   this PRD's own investigation reproduced. Half the real evidence is
   invisible today.
2. **Four vision-doc rows have no view at all**, with a range of actual
   cost once investigated (not assumed):
   - **Forward-drift heatmap by context and horizon** — `grouped_summaries`
     already has `group_dimension`/`group_value`/`horizon_bars` plus
     forward-return/hit-rate/mfe/mae per group. Nearly free: a heatmap
     chart over already-published data, no new upstream work.
   - **MFE/MAE relation** — every one of the 6 real runs (published or
     not) already persists a raw `outcomes.parquet` with per-occurrence
     `forward_return`/`mfe`/`mae` (12K-41K rows) alongside its
     `analytics/` folder. Nearly free: publish a bounded sample, same
     technique as 18A's `equity_curve`/`exposure`.
   - **Adjusted forward drift** — no adjustment method exists anywhere in
     the codebase. Genuinely new; needs a decided methodology (below).
   - **Context timeline / context persistence** — the closest existing
     data (`context.parquet`'s occurrence-scoped
     `context_met_at_available_at`, or `observations.parquet`'s
     true-edge-only events) is not a dense per-bar timeline. Genuinely
     new; needs the same Market-Model-recomputation mechanism 18A's
     `context_expectancy` already built (D-P18-02), applied differently
     (a raw series + a run-length table, not a trade join).

## Goals (v1)

Two sequential milestones, matching 18A's precedent and the maintainer's
already-stated preferred workflow (research/analytics layer first, then
dashboard layer).

### Milestone 1 — Research/analytics layer and publication-boundary fix

- **Fix the root mismatch.** Extend the generic discovery path (catalog
  scanner and the new Signal Research publisher below) to scan
  `user_data/research/` for Signal Research identity and evidence, not
  only `user_data/workspace/`. Exact mechanism (a second storage root
  parameter vs. reconciling the two roots into one going forward) is an
  architect decision — see Handoff.
- **Backfill/generalize the 3 unpublished `signal_research.v2` runs.**
  Their `context.parquet`/`occurrences.parquet`/`outcomes.parquet` shape
  carries the same semantic facts (`analytics/`'s format is a derived
  aggregation over exactly this raw shape); either compute the missing
  `analytics/` tables for these 3 runs from their raw files, or extend
  the publisher to read either shape generically. Architect's call which
  is cheaper — see Handoff.
- **New `mfe_mae_pairs` artifact.** Per run, a bounded sample (same
  `STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS`-style constant, 2000 points,
  deterministic, endpoint-preserving) of `(forward_return, mfe, mae)`
  triples from the run's already-persisted `outcomes.parquet`. No new
  computation — a straight, bounded copy.
- **New `adjusted_forward_drift` artifact.** Empirical-Bayes shrinkage:
  for each `grouped_summaries` row (one (context, horizon) group), shrink
  its `forward_return_mean` toward the run's overall (ungrouped) forward-
  return mean, weighted by that group's `sample_size_complete` relative to
  a decided prior-strength constant — smaller groups shrink further
  toward the global mean, larger groups stay closer to their own mean.
  Exact shrinkage-weight formula and prior-strength constant are an
  architect Wave 0 decision (below), not invented ad hoc per group.
  Computed once in the research/analytics layer; the dashboard applies no
  further shrinkage, per the vision doc's explicit rule.
- **New `context_timeline` and `context_persistence` artifacts.** Reusing
  18A's `state_context_aliases` mechanism (D-P18-02): resolve the run's
  Market Model, recompute Market Analysis components over the published
  dataset, filter to `ComponentKind.STATE` columns the model's expression
  actually references. `context_timeline`: the raw dated series (bounded
  the same way as `equity_curve`, since it is per-bar dense). Missing/
  unlabeled values excluded per this component's contract, not fabricated.
  `context_persistence`: run-length encoding of that series (a table of
  `label`, `start_at`, `end_at`, `duration_bars` — analogous to 18A's
  `drawdown_episodes` shape, generalized from "peak-to-recovery" to "same-
  label run").

### Milestone 2 — Dashboard layer

- **Signal Research overview table** (new — today there is only a
  selector, no cross-run table): every safely-projected run, research
  question, Market/Signal Model identities, dataset/instrument,
  evaluation interval/timeframe, direction, outcome horizon(s), sample/
  completion counts, persisted outcome measures, quality warnings.
  Sortable via the same native-`st.dataframe`-header pattern 18A's
  Milestone 2b established — no new sort-UI code.
- **Forward-drift heatmap by context and horizon**, from `grouped_summaries`.
- **MFE/MAE relation** scatter, from the new `mfe_mae_pairs` artifact.
- **Adjusted forward drift** view, from the new artifact, clearly labeled
  as a shrinkage-adjusted measure distinct from the raw `grouped_summaries`
  mean beside it — never silently replacing the raw figure.
- **Context timeline** chart and **context persistence** table, from the
  two new artifacts, honestly reporting "unavailable" when a run's Market
  Model has no `STATE`-kind dependency (the same honest-empty pattern 18A
  established for `context_expectancy`).
- Signal Research can contain several horizons/directions in one run
  (vision doc's explicit warning); every view above operates on one
  explicit (horizon, direction) slice at a time, chosen by the visitor —
  never silently collapsed to one score per run.

## Non-goals (v1)

- **18D (Robustness Research evidence view)** — separate, later PRD.
- **Reconciling `user_data/research/` and `user_data/workspace/` for any
  workflow other than Signal Research** — Strategy Research's own root is
  already correct (18A); this PRD fixes Signal Research's root mismatch
  only, not a general storage-layout migration.
- **A general v1-vs-v2 signal-schema migration tool** — the backfill/
  generalization in Milestone 1 covers exactly the 3 existing
  `signal_research.v2` runs found during this PRD's investigation, not a
  speculative future schema.
- **Any change to how Signal Research itself runs or persists new data**
  going forward beyond what's needed to fix the root mismatch — this PRD
  is a publication/dashboard fix, not a Signal Research engine change.

## Success metrics

1. **Research Catalog shows the true Signal count** (6, or however many
   are safely identifiable) instead of 0.
2. **All 6 real Signal Research runs are projected**, not just 3 — verified
   by a dedicated test, not just absence of a failing assertion (mirroring
   18A's `test_discovery_excludes_robustness_experiment_child_runs`-style
   verification discipline).
3. **`mfe_mae_pairs` and `context_timeline`/`context_persistence` are
   published for at least one run each**, with at least one run showing
   real, non-trivial context data (mirroring 18A's canonical-example
   verification against real data, not just a synthetic fixture).
4. **`adjusted_forward_drift` values differ from raw `grouped_summaries`
   means precisely in proportion to sample size** — small-sample groups
   shrink measurably toward the global mean; this is checked directly,
   not merely "a number appears."
5. **No new metric is computed by the dashboard at request time** — every
   number traces to a Milestone 1 persisted artifact, verifiable by code
   review against ADR-0034/0035, exactly as 18A required.

## Riskiest assumption

**That the empirical-Bayes shrinkage formula, once an architect actually
specifies its prior-strength constant, produces intuitively sensible
adjustments on the real data** — this PRD commits to the *technique*
(shrinkage weighted by sample size) but not yet to specific numbers. If
Wave 0's proposed constant produces adjustments that look wrong against
the 6 real runs' actual group sizes (e.g. barely moving anything, or
over-flattening every group toward the mean), that is a stop-and-report
finding for the architect to recalibrate, not a reason to ship an
unexamined formula. Secondary risk, lower: whether the 3 unpublished
`signal_research.v2` runs' raw files actually contain everything needed
to derive the same `analytics/` shape the 3 already-published runs have
— Milestone 1's first implementation step must confirm this against the
real files before assuming it, the same discipline 18A's Wave 0 applied
to the Market-Model-boolean-only finding.

## Constraints

- Milestone 2 does not start until Milestone 1's artifacts exist for at
  least one run — same hard sequencing gate as 18A.
- No new ADR expected by default: the root-mismatch fix and the two new
  per-run artifacts follow 18A's already-established
  `publication/workspace.py` sibling-function and `analytics/`-folder
  conventions. If the root-mismatch fix turns out to need reconciling the
  two physical roots into one (rather than scanning both), that finding
  earns its own ADR at that point — not assumed here.
- Every Wave 0 / architect decision set goes back to the maintainer for
  explicit review before implementation starts.

## User story

As the maintainer, I want the Signal Research evidence page to show every
real run that exists — not silently drop half of them because of a
storage-root mismatch nobody had noticed — and to cover the vision doc's
remaining rows using the cheapest correct data source for each: a
heatmap and an MFE/MAE scatter from data that already exists, an
adjusted-drift measure computed once with a real, decided shrinkage
formula, and a context timeline built the same way 18A's context
expectancy already proved out, so none of this becomes a second
ad hoc mechanism to maintain.

## Open questions

- **Exact shrinkage-weight formula and prior-strength constant** for
  `adjusted_forward_drift` — architect proposes, backed by a look at the
  6 real runs' actual group-size distribution rather than a guess,
  mirroring Phase 19 Wave 0's "principled starting point, explicitly
  recalibratable" precedent.
- **Root-mismatch fix mechanism**: scan both `user_data/research/` and
  `user_data/workspace/` going forward (two storage roots, one dashboard),
  or migrate/symlink so Signal Research data lives under one root like
  Strategy Research's already does — architect's call, checked against
  whatever actually created the two-root split historically (worth a
  quick look at when/why `user_data/research/` vs `user_data/workspace/`
  diverged before deciding).
- **Backfill vs. generic dual-format read** for the 3 `signal_research.v2`
  runs — whichever is actually cheaper once the architect inspects what
  computing `analytics/`'s tables from raw `occurrences`/`outcomes`/
  `context` requires (this PRD's own investigation did not attempt that
  computation, only confirmed the raw files exist).
- **`context_persistence`'s run-length table shape** — exact column set
  (mirroring `drawdown_episodes`'s `episode_id`/`peak_at`/`trough_at`/
  `duration_bars`/`recovery_bars` shape, generalized to
  `run_id`/`label`/`start_at`/`end_at`/`duration_bars`) is a natural
  default, not fixed here as binding.

## Handoff

Architect: continue Wave 0 covering (a) the root-mismatch fix mechanism,
(b) the 3 `signal_research.v2` runs' backfill-vs-dual-format-read
decision, (c) the shrinkage formula and prior-strength constant for
`adjusted_forward_drift`, and (d) `context_persistence`'s exact table
shape. The MFE/MAE-pairs mechanism (bounded sample from already-persisted
`outcomes.parquet`), the context-timeline mechanism (reusing 18A's
`state_context_aliases`) and the milestone ordering (analytics before
dashboard) are already resolved — see Goals; do not re-litigate them.
