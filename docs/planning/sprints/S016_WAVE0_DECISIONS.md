# Sprint 016 — Wave 0 Architecture Decisions (Robustness Research MVP)

## Metadata

```text
Task: S016-T001
Sprint: 016 — Robustness Research MVP (Phase 7)
Status: ACCEPTED (planning)
Planned Start: 2026-07-15
Branch: sprint/robustness-mvp
Direction: docs/planning/sprints/SPRINT_016.md
Depends on: SPRINT_013–015 merged to main (ADR-0016, ADR-0017, ADR-0018)
Scope: fourth independent research workflow — experiment orchestration, validation analytics, verdict report
```

---

## 0. Rationale

Sprints 008–010 (Signal Research) and 013–014 (Strategy Research + dashboard) answer:

```text
Does the signal show edge?  →  What is the PnL of a complete Strategy Model?
```

Phase 7 answers a different question:

```text
Is the observed edge stable enough to justify paper execution or deeper validation?
```

A top parameter configuration from a grid sweep is **not** validation. Robustness produces a
**documented verdict** with explicit assumptions — separate from ranking and base simulation.

---

## 1. Fourth independent workflow

**Decision D-S016-01:** Robustness Research is workflow-independent (ADR-0011 pattern):

```text
Signal Research      — signal behaviour, no execution
Strategy Research    — bar-sequential simulation, persisted envelope
Robustness Research  — orchestrates many strategy runs + read-only validation analytics
Execution            — future replay/paper/live (Phase 8+)
```

Robustness **must not** mutate Strategy Research envelopes. It may **reference** persisted
`strategy_research/<run_id>/` artifacts and spawn **new** child strategy runs under an experiment.

---

## 2. Compute vs analytics boundary

**Decision D-S016-02:** Split orchestration and analytics (ADR-0013 pattern):

| Layer | Owns |
|-------|------|
| `run_robustness_experiment` | experiment plan, batch `run_strategy_research`, registry, resume |
| `analyze_robustness_experiment` | rankings, walk-forward stitching, stress replay, Monte Carlo, diagnostics, verdict |

Analytics is **read-only** over persisted experiment and child-run artifacts. No hidden re-simulation
inside analytics except explicitly declared **stress re-runs** (commission/slippage/delay scenarios)
recorded as separate child runs.

---

## 3. Experiment kinds (MVP)

**Decision D-S016-03:** One `RobustnessExperiment` supports these kinds (combinable in one report):

| Kind | Purpose |
|------|---------|
| `PARAMETER_SWEEP` | Grid over Strategy Model parameters (and declared analysis params) |
| `WALK_FORWARD` | Rolling / expanding windows; train-only selection; OOS evaluation |
| `STRESS_TEST` | Commission, slippage, entry/exit delay, remove top trades/days |
| `MONTE_CARLO` | Trade-level resampling and path envelopes |
| `STATISTICAL_DIAGNOSTICS` | Temporal stability, PnL concentration, IS/OOS degradation |

MVP does **not** require all kinds in the first implementation PR. Wave 1 delivers infrastructure;
later waves attach kind-specific planners and analyzers.

---

## 4. Parameter sweep scope

**Decision D-S016-04:** MVP sweep targets:

```text
Strategy Model parameters   — e.g. exit_after_bars, volatility threshold, pivot_range
SimulationAssumptions       — only in STRESS_TEST / explicit stress grids (not mixed into PARAMETER_SWEEP ranking by default)
```

Canonical vertical slice: `high_vol_higher_low_fixed_exit` on published continuous NQ OHLCV
(`SPRINT_013` example).

Sweep generates a **finite grid** from declarative experiment spec — not ad-hoc script loops.

---

## 5. Walk-forward semantics

**Decision D-S016-05:** Walk-forward MVP rules (binding):

```text
1. Parameter selection uses TRAIN window metrics only.
2. Selected parameters are frozen for the paired OOS window.
3. OOS equity segments are concatenated in time order → stitched OOS equity curve.
4. No peeking: OOS window data must not influence train selection for the same fold.
5. Both rolling and expanding train windows are supported.
```

Fold definitions use UTC `TimeRange` on the published OHLCV dataset — same as Strategy Research.

---

## 6. Monte Carlo semantics (MVP)

**Decision D-S016-06:** Monte Carlo in MVP operates on **persisted trade outcomes** — not synthetic
price paths, order book, or market impact.

| Method | Definition | Replacement |
|--------|------------|-------------|
| **Trade-sequence shuffle** | Random permutation of trade order; same multiset of trade PnL | Without replacement |
| **Trade PnL bootstrap** | Resample trades with replacement to build synthetic equity paths | With replacement |
| **Block bootstrap** | Resample contiguous blocks (default: session-day blocks) | With replacement, preserves short-range dependence |
| **Equity path envelope** | Percentile bands (e.g. p5/p50/p95) over N simulated paths | Derived from the above |

Outputs per experiment (minimum):

```text
path_count
percentile_equity (p5, p50, p95) by bar index or trade index
distribution_summary (terminal equity, max drawdown, Sharpe proxy)
probability_metrics (e.g. P(max_dd > threshold), P(terminal_pnl < 0))
```

**Explicitly out of MVP Monte Carlo:**

- price-path simulation,
- order-book fill uncertainty,
- correlated multi-asset paths,
- Bayesian MCMC / genetic search.

Monte Carlo results feed the **verdict** — they do not alone imply PASS.

---

## 7. Stress testing semantics

**Decision D-S016-07:** Stress scenarios are **versioned scenario specs** that produce child Strategy
Research runs (or deterministic post-processors where only assumptions change):

```text
commission_per_side multipliers
slippage_bps multipliers
entry_delay_bars / exit_delay_bars
remove_top_n_trades_by_pnl
remove_top_n_days_by_pnl
```

Each scenario records `scenario_id`, assumptions fingerprint, and child `run_id`.

---

## 8. Statistical diagnostics (MVP)

**Decision D-S016-08:** Diagnostics are computed on persisted trades/equity and experiment metadata:

```text
temporal_stability        — metric drift across time buckets (month / quarter)
pnl_concentration         — share of total PnL from top k trades / days
is_oos_degradation        — train vs OOS metric deltas (walk-forward linked)
neighbor_parameter_stability — local grid sensitivity (PARAMETER_SWEEP linked)
isolated_optimum_detection   — single-cell peak surrounded by poor neighbors
```

---

## 9. Verdict model

**Decision D-S016-09:** Every completed experiment emits `RobustnessVerdict`:

```text
verdict: PASS | CONDITIONAL | FAIL
summary: plain-language headline
strengths: bullet list
weaknesses: bullet list
blocking_issues: optional list (hard FAIL reasons)
assumptions_fingerprint: hashes experiment spec + framework version
```

Rules:

- Ranking **best config** is reported separately — never equated with PASS.
- PASS requires explicit criteria in experiment spec (thresholds on OOS, Monte Carlo percentiles,
  stress survivability) — no universal magic score in MVP.
- CONDITIONAL = promising but fails one or more soft gates; FAIL = hard gate breach or unstable OOS.

---

## 10. Storage layout

**Decision D-S016-10:** Persist under `storage_root` (parallel to strategy research):

```text
robustness_experiments/<experiment_id>/
  manifest.json              — experiment spec, kind, status, lineage
  registry.json              — planned runs, completed run_ids, resume cursor
  folds/                     — walk-forward fold definitions (if applicable)
  child_runs.jsonl           — mapping config → strategy_research run_id
  analytics/                 — parquet/json summaries (rankings, MC envelopes, diagnostics)
  report/                    — rendered Robustness Report HTML (Phase A offline)
```

Child Strategy Research runs remain in `strategy_research/<run_id>/` — referenced, not duplicated.

Optional `experiment_id` on Strategy Research manifest links child runs to parent experiment
(field already exists on `StrategyResearchRunManifest`).

---

## 11. Resume and reproducibility

**Decision D-S016-11:**

```text
experiment_id     — stable operator-chosen or content-derived id
config_fingerprint — hash of each grid cell / scenario / fold params
resume            — registry skips completed child runs; reruns only failed/pending
reproducibility   — manifest records framework version, dataset refs, date ranges, RNG seed for Monte Carlo
```

---

## 12. Robustness Report (MVP)

**Decision D-S016-12:** One offline HTML report per experiment (ADR-0017 pattern):

```text
sections:
  Overview — verdict, experiment kind, dataset, strategy family
  Parameter landscape — heatmaps, ranking table, neighbor stability
  Walk-forward — fold table, stitched OOS equity, IS/OOS degradation
  Stress — scenario comparison table
  Monte Carlo — equity envelope chart, percentile table, tail probabilities
  Diagnostics — temporal stability, PnL concentration
  Assumptions — full experiment spec fingerprint
```

Plotly optional for MC/diagnostic charts; verdict readable without charts.

---

## 13. Out of scope (Phase 7 MVP)

Binding exclusions (defer to later phases):

```text
order-book Monte Carlo, market impact models
portfolio-level / cross-asset robustness
distributed experiment execution
Bayesian optimization, genetic optimization
PBO, CSCV, Deflated Sharpe, White's Reality Check, Hansen's SPA
live / paper execution gates (Phase 8)
```

---

## 14. Decision index

| ID | Summary |
|----|---------|
| D-S016-01 | Fourth independent Robustness workflow |
| D-S016-02 | Orchestration vs read-only analytics split |
| D-S016-03 | Experiment kinds enum |
| D-S016-04 | Parameter sweep vs stress assumptions |
| D-S016-05 | Walk-forward train/OOS/stitch rules |
| D-S016-06 | Monte Carlo on trades (shuffle, bootstrap, block, envelope) |
| D-S016-07 | Stress scenarios as versioned child runs |
| D-S016-08 | Statistical diagnostics set |
| D-S016-09 | PASS / CONDITIONAL / FAIL verdict |
| D-S016-10 | `robustness_experiments/` storage layout |
| D-S016-11 | Resume + RNG seed reproducibility |
| D-S016-12 | Offline Robustness Report HTML |

---

## 15. References

- `docs/planning/sprints/SPRINT_016.md`
- `docs/adr/ADR-0019-robustness-research-mvp.md`
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/vision/WORKFLOWS_AI_ADR_UPDATED.md` §4.20–4.21
