# Research Methodologies (As-Implemented)

> **Reference doc** — [as-implemented layer](README.md).  
> Data paths and diagrams: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Package index: [MODULE_MAP.md](MODULE_MAP.md).

This document describes **every research-oriented methodology** in the framework today: what question each
answers, how workflows relate to each other, and where to start in code and CLI.

**Important:** workflows are **independent capabilities** that share domains (Market Data, Market Analysis,
declarative models). They are **not** mandatory stages of one pipeline.

```text
                    Shared foundations
         Market Data · Market Analysis · Declarative models
                               │
       ┌───────────┬───────────┼───────────┬───────────┐
       │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼
  Signal      Model         Strategy    Robustness   (Future:
  Research    Research      Research    Research     Execution)
  (Phase 5)   Methodology   (Phase 6A)  (Phase 7)
              (Phase 5B)
```

---

## 1. Methodology map

| Methodology | Research question | Phase / track | Sprint | ADR | Primary orchestration |
|-------------|-------------------|---------------|--------|-----|------------------------|
| **Market Analysis** | What do reusable analytical components compute on OHLCV? | Foundation | 003–005 | ADR-MA-* | `run_analysis`, `DependencyPlanner` |
| **Declarative models** | How do Market × Signal models evaluate on one table? | Foundation | 006 | — | `evaluate_models` |
| **Signal Research** | Do model states / signals predict forward price behaviour? | Phase 5 | 008–010 | ADR-0011–0013 | `run_signal_research` |
| **Model Research Methodology** | Is the study reproducible, bounded, and diagnostically sound? | Phase 5B | 017 | ADR-0020 | Definition spec → run → analyze → report |
| **Strategy Research** | Does a full strategy (entry/exit/risk) produce acceptable PnL? | Phase 6A | 013–014 | ADR-0016–0017 | `run_strategy_research` |
| **Robustness Research** | Does edge survive parameter, regime and stress variation? | Phase 7 | 016 | ADR-0019 | `run_robustness_experiment` |

**Computation vs analytics (binding rule):** every methodology **persists factual run artifacts first**,
then exposes **read-only analytics and HTML** that must not re-run model evaluation or simulation unless
inputs change (ADR-0013, ADR-0017, ADR-0019, ADR-0020).

---

## 2. Shared foundations

### 2.1 Market Data

All research consumes **published** `DatasetRef` values from a runtime `storage_root` (typically
`user_data/storage` or `user_data/storage_nq_half_year`). Ingest, finalize and publish are documented in
[DATA_WORKFLOWS.md §3](DATA_WORKFLOWS.md#3-market-data--ingest-workflow).

**Continuous NQ half-year reference:** `NQ.c.0|ohlcv|1m|derived|volume-rth-close@1` — **177,507** bars
(Jul 2025 – Jan 2026). Scale table: [DATA_WORKFLOWS §1.1](DATA_WORKFLOWS.md#11-reference-scale-nq-half-year-demo).

### 2.2 Market Analysis

Reusable components (ATR, volatility state, swing structure, MTF alignment, …) execute once per plan on an
`AnalysisDataView` and produce `AnalysisResult` facts.

```text
Published DatasetRef
  → load_analysis_data_view
  → DependencyPlanner.build_plan
  → SequentialBatchExecutor.execute
  → AnalysisWorkspace / AnalysisResult
```

Entry points: `application.market_analysis`, `market_analysis.planning`, `market_analysis.execution`.  
Deep flow: [DATA_WORKFLOWS §5–6](DATA_WORKFLOWS.md#5-market-analysis--data-input-bridge).

Market Analysis is **not** a standalone “research methodology” with its own envelope — it is the **compute
substrate** for declarative models and downstream research workflows.

### 2.3 Declarative models (`evaluate_models`)

Sprint 006 adds Market Model and Signal Model definitions evaluated on a **shared analysis table** (one
`run_analysis` pass deduplicated across models).

```text
model_authoring (optional DSL)
  → model_expression IR
  → evaluate_models
  → MarketModelEvaluator / SignalModelEvaluator
```

Canonical examples: `high_volatility`, `higher_low_long`, combined variants — see
`application/model_evaluation/canonical_examples.py`.

This layer is shared by **Signal Research**, **Strategy Research** and inspection spikes; it is not a
persisted research run on its own.

---

## 3. Signal Research (Phase 5)

**Question:** Does the studied model describe repeatable forward price behaviour (returns, MFE, MAE, hit
rate) — **without** order simulation or PnL?

### 3.1 Research scopes (ADR-0012)

| Scope | Models evaluated | Typical facts |
|-------|------------------|---------------|
| `MARKET_MODEL_ONLY` | Market model TRUE_EDGE observations | `MarketModelObservation` → forward outcomes |
| `SIGNAL_MODEL_ONLY` | Signal model ON_EVENT occurrences | `SignalOccurrence` → forward outcomes |
| `MARKET_AND_SIGNAL` | Both + context alignment at `available_at` | Occurrences + `ContextFact` → outcomes |

### 3.2 Workflow

```text
Published DatasetRef + scope + horizons
  → run_signal_research
  → immutable run envelope at {storage_root}/{run_id}/
       manifest.json
       observations.parquet / occurrences.parquet / context.parquet (scope-dependent)
       outcomes.parquet (long format, per horizon)
  → analyze_signal_research_run (read-only Polars aggregates)
  → optional HTML (presentation-only spikes)
```

**Entry points:** `application.signal_research.run_signal_research`,
`application.signal_research.analyze_signal_research_run`.

**Persistence:** ADR-0011 envelope schema v1/v2; deterministic `run_id` from material inputs.

**Integration tests:** `tests/integration/test_s008_run_signal_research.py`,
`test_s009_*`, `test_s010_signal_research_analytics.py`.

### 3.3 What Signal Research does not do

- Exit / risk / position simulation
- Equity curve or trade ledger
- Parameter optimization or robustness verdicts

Those belong to Strategy Research and Robustness Research respectively.

---

## 4. Model Research Methodology (Phase 5B)

**Question:** Can a maintainer run a **documented, bounded study protocol** with quality diagnostics and a
professional offline dashboard — on top of the Signal Research kernel?

Model Research Methodology is a **methodology layer on Signal Research**, not a separate fourth workflow
(ADR-0020).

### 4.1 Declarative study contract

`SignalResearchDefinitionSpec` (YAML/JSON) records:

```text
research_id, scope, dataset_ref, time_range
market_model / signal_model aliases
horizons (5m, 15m, 30m, 60m on 1m base)
scope-appropriate baseline (MODEL_ACTIVE / AFTER_SIGNAL / SIGNAL_ONLY)
occurrence_policy (KEEP_ALL, FIRST_PER_BAR, COOLDOWN — definition level)
grouping (month, session, time_of_day)
quality_rules (minimum sample size, period concentration, …)
optional model_family (bounded manual variants)
```

Example fixture: `tests/fixtures/signal_research/nq_half_year_definition.yaml`.

### 4.2 Workflow

```text
SignalResearchDefinitionSpec
  → resolve_signal_research_definition + map_definition_to_run_request
  → run_signal_research
  → analyze_signal_research_run + SignalResearchQualityFlags
  → persist_signal_research_analytics → analytics/summary.json (optional sidecar)
  → build_signal_research_report → offline Plotly HTML (10 sections)
  → optional run_signal_research_family_experiment (bounded variant comparison)
```

**CLIs:** `scripts/signal_research/run_signal_research.py`,
`analyze_signal_research.py`, `render_signal_research_report.py`, `run_model_family.py`.

**Report sections (MVP v1):** run metadata, KPI cards (sample size beside every metric), metrics by horizon,
forward-return / MFE / MAE histograms, grouped month/session/time-of-day, baseline marginal contribution,
diagnostics + quality flags.

### 4.3 NQ half-year vertical slice

```bash
uv pip install plotly
uv run python scripts/demo/run_model_research_nq_demo.py --open
```

| Output | Content |
|--------|---------|
| `demo/output/08_model_research_nq_half_year.html` | Index linking three scope reports |
| `demo/output/model_research/market_model_only.html` | `high_volatility` |
| `demo/output/model_research/signal_model_only.html` | `higher_low_long` |
| `demo/output/model_research/market_and_signal.html` | Combined + SIGNAL_ONLY baseline |

**Reference timing (2026-07-15, laptop):** full demo on 177,507 bars, 3 scopes, 4 horizons — **~16.5 min**
wall clock. Strategy Research on the same dataset is **~6 s** (simulation-heavy vs occurrence/outcome
materialization across scopes). Profiling follow-up tracked separately.

**Fixture fallback:** `--fixture` — ES CSV, single 5m horizon, signal + combined scopes only.

Detail: [DATA_WORKFLOWS §3.13](DATA_WORKFLOWS.md#313-model-research-methodology-sprint-017--phase-5b).

---

## 5. Strategy Research (Phase 6A)

**Question:** Does a **complete strategy** (market × signal gating × exit × risk) produce acceptable
simulated PnL on historical bars?

### 5.1 Workflow

```text
Published OHLCV DatasetRef
  → run_strategy_research
  → query_historical_columnar → shared evaluate_models
  → build_gated_entry_signals
  → simulate_from_columnar (Numba fixed-bars kernel)
  → strategy_research/<run_id>/{manifest.json, trades.parquet, equity.parquet}
  → analyze_strategy_research_run (read-only summary)
  → build_strategy_dashboard_view_model
  → render_strategy_research_dashboard → standalone HTML (Lightweight Charts)
```

**Simulation assumptions:** `NEXT_BAR_OPEN` fills; fingerprint in manifest (ADR-0016).

**CLIs:** `scripts/strategy_research/run_strategy_research.py`,
`scripts/strategy_research/render_strategy_dashboard.py`,
`scripts/market_data/run_half_year_backtest.py` (NQ half-year orchestration + `--profile`).

**Dashboard boundary:** renderer is presentation-only; no re-simulation (ADR-0017).

Detail: [DATA_WORKFLOWS §3.8–3.9](DATA_WORKFLOWS.md#38-strategy-research-run-envelope-sprint-013).

### 5.2 Relation to Signal Research

Strategy Research **reuses** `evaluate_models` but does **not** require a persisted Signal Research run.
Signal Research studies **forward behaviour of facts**; Strategy Research studies **PnL under execution
assumptions**.

---

## 6. Robustness Research (Phase 7)

**Question:** Does a strategy edge survive parameter variation, walk-forward regimes, stress scenarios and
Monte Carlo resampling?

### 6.1 Workflow

```text
RobustnessExperimentSpec (kinds + thresholds)
  → run_robustness_experiment / run_*_experiment
       batch Strategy Research child runs + resume registry
  → analyze_*_experiment (read-only per kind)
  → analyze_robustness_experiment → PASS / CONDITIONAL / FAIL verdict
  → render_robustness_report → standalone HTML dashboard
```

**Experiment kinds (MVP):** parameter sweep, walk-forward, stress test, Monte Carlo, statistical
diagnostics.

**CLIs:** `scripts/robustness_research/` (`run_*`, `analyze_*`, `render_robustness_report.py`).

**Demo:** `scripts/demo/run_robustness_demo.py` → `demo/output/07_robustness_dashboard.html`.

Detail: [DATA_WORKFLOWS §3.14](DATA_WORKFLOWS.md#314-robustness-research-sprint-016--phase-7).

**Boundary:** stress and Monte Carlo operate on persisted **trades**; analytics never re-simulates
(ADR-0019).

---

## 7. Showcase bundles (offline HTML)

| Script | Artifact | Workflows demonstrated |
|--------|----------|------------------------|
| `scripts/demo/run_portfolio_demo.py` | `demo/output/index.html` | Strategy dashboard, Signal analytics spikes, model/occurrence/MTF inspection |
| `scripts/demo/run_model_research_nq_demo.py` | `08_model_research_nq_half_year.html` | Model Research Methodology — 3 scopes |
| `scripts/demo/run_robustness_demo.py` | `07_robustness_dashboard.html` | Robustness Research verdict dashboard |

Portfolio guide: [scripts/demo/README.md](../../scripts/demo/README.md).

---

## 8. Choosing a methodology

| If you need to… | Use |
|-----------------|-----|
| Validate a component or indicator in isolation | Market Analysis + inspection spikes |
| Test whether a signal predicts forward returns | Signal Research or Model Research Methodology |
| Document a reproducible study with quality flags and HTML report | Model Research Methodology |
| Compare a small manual list of model variants (bounded) | `run_signal_research_family` |
| Measure simulated PnL, drawdown, trade count | Strategy Research |
| Stress-test survivability across parameters and regimes | Robustness Research |
| Import or materialize data | Market Data workflows (not research) |

**Typical progression (optional, not enforced):**

```text
Market Data ready
  → Model Research (edge discovery)
  → Strategy Research (PnL simulation)
  → Robustness Research (validation)
```

---

## 9. Persistence layout (research runs)

```text
{storage_root}/
  {run_id}/                          # Signal Research run (top-level)
    manifest.json
    *.parquet
    analytics/summary.json           # optional cached analytics (Phase 5B)
    report/report.html               # optional in-run report path
  strategy_research/{run_id}/
    manifest.json, trades.parquet, equity.parquet
  robustness_experiments/{experiment_id}/
    manifest.json, child run registry, per-kind artifacts
  signal_research_experiments/{experiment_id}/   # model family experiments
```

`user_data/` is runtime-only and never imported from `src/`.

---

## 10. Quick entry-point index

| Methodology | Application module | Key functions |
|-------------|-------------------|---------------|
| Market Analysis | `application.market_analysis` | `load_analysis_data_view`, `run_analysis` |
| Model evaluation | `application.model_evaluation` | `evaluate_models` |
| Signal Research | `application.signal_research` | `run_signal_research`, `analyze_signal_research_run` |
| Model Research | `application.signal_research` + `research/signal_research` | `resolve_signal_research_definition`, `render_signal_research_report` |
| Strategy Research | `application.strategy_research` | `run_strategy_research`, `build_strategy_dashboard_view_model` |
| Robustness Research | `application.robustness_research` | `run_robustness_experiment`, `analyze_robustness_experiment` |

Full package map: [MODULE_MAP.md](MODULE_MAP.md).

---

## Maintenance

Update this document when:

- a new research methodology or phase is merged,
- public workflow contracts (definition spec, envelope schema, CLI trio) change,
- showcase demos or reference timings change materially.

After sprint closure waves: sync [CURRENT_STATUS.md](../planning/CURRENT_STATUS.md) and the sprint doc in
`docs/planning/sprints/`.
