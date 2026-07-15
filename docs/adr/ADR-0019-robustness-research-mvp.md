# ADR-0019 — Robustness Research MVP (Phase 7)

## Status

ACCEPTED (Sprint 016)

## Context

Phase 6A (Sprints 013–014) delivers Strategy Research simulation and inspection dashboards on
published OHLCV. Sprint 015 delivers continuous NQ datasets suitable for multi-month evaluation.

The platform can answer **what a Strategy Model earned in-sample**, but not whether that result is
**stable under parameter perturbation, costs, time splits, or resampled trade paths**.

`ROADMAP.md` Phase 7 lists walk-forward, Monte Carlo, and cost sensitivity at a high level.
Sprint 016 Wave 0 (`S016_WAVE0_DECISIONS.md`) narrows the first vertical slice.

## Decision

### Workflow identity

Introduce **Robustness Research** as a fourth workflow independent from Signal Research, Strategy
Research and Execution:

```text
run_robustness_experiment     — plan + batch execute + registry + resume
analyze_robustness_experiment — read-only validation analytics + verdict
render_robustness_report      — offline HTML (Phase A)
```

Robustness orchestrates `run_strategy_research`; it does not replace or fork the simulator kernel.

### Experiment specification

A **RobustnessExperiment** declares one or more kinds:

```text
PARAMETER_SWEEP
WALK_FORWARD
STRESS_TEST
MONTE_CARLO
STATISTICAL_DIAGNOSTICS
```

The spec records dataset refs, base strategy template, grids, fold policy, stress scenarios,
Monte Carlo path count + RNG seed, and PASS/CONDITIONAL/FAIL thresholds.

### Monte Carlo (trade-level)

MVP Monte Carlo uses **persisted simulated trades** only:

```text
trade-sequence shuffle   — permutation without replacement
trade PnL bootstrap      — resample trades with replacement
block bootstrap          — resample session-day blocks with replacement
equity path envelope     — percentile bands (p5/p50/p95) over N paths
```

Monte Carlo outputs include terminal-equity and max-drawdown distributions and tail probabilities.
They inform the verdict; they are not standalone proof of edge.

**Not in MVP:** price-path MC, order-book simulation, market impact, Bayesian/genetic optimization.

### Walk-forward

```text
parameter selection on TRAIN only
evaluation on paired OOS
stitched OOS equity curve in chronological order
rolling and expanding train windows
```

### Verdict artifact

Every analyzed experiment produces `RobustnessVerdict`:

```text
PASS | CONDITIONAL | FAIL
+ strengths, weaknesses, blocking_issues, assumptions_fingerprint
```

Best grid rank is reported separately and **must not** be labeled validation.

### Persistence

```text
<storage_root>/robustness_experiments/<experiment_id>/
  manifest.json, registry.json, child_runs.jsonl, analytics/, report/
```

Child runs live under `strategy_research/<run_id>/` with optional `experiment_id` linkage.

### Domain packages (target)

```text
research/robustness/              experiment spec, verdict, MC/stress/fold models
research/datasets/robustness.py   envelope + repository (mirror strategy_research pattern)
application/robustness_research/  run_robustness_experiment, analyze_robustness_experiment
research/reporting/robustness/    offline HTML renderer (Phase A)
```

### CLI (target)

```text
scripts/robustness_research/run_robustness_experiment.py
scripts/robustness_research/analyze_robustness_experiment.py
scripts/robustness_research/render_robustness_report.py
```

Canonical slice: `high_vol_higher_low_fixed_exit` on published `NQ.c.0` continuous 1m OHLCV.

## Consequences

### Positive

- Clear gate between historical research and paper execution (Phase 8).
- Reuses Strategy Research envelopes — no duplicate simulation semantics.
- Monte Carlo and bootstrap are explicit, reproducible (RNG seed in manifest).
- Verdict-oriented reporting fits portfolio and risk review narratives.

### Negative

- Large grids multiply Strategy Research runs — needs resume and incremental analytics.
- Walk-forward + sweep combinatorics can explode without grid size limits in MVP.
- Trade-level Monte Carlo ignores path dependency from overlapping positions if exit logic changes
  under resampling — MVP documents shuffle as **order-risk** diagnostic, not fill realism.

### Follow-up (post-MVP)

- PBO / CSCV / deflated Sharpe family (explicitly deferred).
- Distributed experiment runner.
- Dashboard Phase B lazy-load for large MC path samples.

## References

- `docs/planning/sprints/SPRINT_016.md`
- `docs/planning/sprints/S016_WAVE0_DECISIONS.md`
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/planning/ROADMAP.md` §11
