# Module Map

> **Reference doc** — [as-implemented layer](../README.md).  
> Data flows: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Index: [docs/README.md](../README.md).

Package map for `src/trading_framework/`: responsibility, dependencies, status, entry points.

**Status legend:** ✅ implemented · 🟡 partial / in sprint · ⬜ skeleton · 📘 deep doc elsewhere

Last updated: 2026-07-14 (Sprint 015 on `main`; simulation refactor + columnar OHLCV on `main`)

**Roadmap:** parallel capability tracks — `docs/planning/ROADMAP.md` §3. Phase 2A–2C.4, 4A, 5, 6A delivered on `main`. Portfolio demo: `scripts/demo/`.

---

## Layer Overview

```text
application/          use cases — orchestrates domain + infrastructure
    ↓ uses
market/               market domain models and repository protocols
market_analysis/      analysis domain — components, planning, execution
model_expression/     declarative expression IR, validation, evaluation
model_authoring/      user-facing model DSL (compiles to model_expression)
market_model/         Market Model definitions and evaluator
signal_model/         Signal Model definitions, firing, emissions
infrastructure/       adapters — CSV, Parquet, file registry
core/, time/, config/ shared primitives
strategy/, research/         Signal Research MVP (Sprint 008–010) ✅; Strategy Research MVP (Sprint 013) ✅; Strategy dashboard (Sprint 014) ✅
execution/, events/          ⬜ future domains
```

**Boundary:** `src/trading_framework/` must not import `user_data/`. User-owned paths are passed in at runtime.

---

## Shared Foundations

### `core/` ✅

| | |
|---|---|
| **Responsibility** | Identifiers, price types, framework exceptions |
| **Talks to** | Used everywhere; no domain imports |
| **Key paths** | `identifiers/base.py`, `types/price.py`, `exceptions.py` |

### `time/` ✅

| | |
|---|---|
| **Responsibility** | UTC instants, timeframes, `Clock` protocol, batch session resolution (S005) |
| **Talks to** | `market`, `market_analysis` (time ranges, session metadata) |
| **Key paths** | `models/utc_instant.py`, `models/timeframe.py`, `clocks/`, `sessions/` (`TradingSessionResolver`, `CmeEsRthSessionResolver`) |

### `config/` ✅

| | |
|---|---|
| **Responsibility** | Framework configuration loading |
| **Talks to** | Application entry points (paths from caller) |
| **Key paths** | `models.py`, `loader.py` |

---

## Market Data (Sprint 002 — Phase 2A; Sprint 011 — Phase 2B + 2C.1; Sprint 012 — Phase 2B.3; Sprint 015 — Phase 2C.4) ✅

### OHLCV (Phase 2A)

End-to-end flow:

```text
CSV file
  → import_external_dataset
  → normalize (UTC OHLCV)
  → validate
  → Parquet write (bars.parquet)
  → register in FileDatasetRegistry
  → finalize_dataset → publish_dataset
  → query_historical → list[MarketBar]  (boundary API)
  → query_historical_columnar → OhlcvColumnBatch  (batch research hot path)
```

### Trades archive (Phase 2B + 2C.1 — Sprint 011)

End-to-end flow:

```text
Databento DBN trades archive
  → import_databento_trades_archive
  → inspect + source SHA-256
  → chunked decode → MarketTrade
  → validate → day-partitioned Parquet
  → import_manifest.json
  → register WORKING → finalize → publish
  → query_trades → list[MarketTrade]
```

CLI: `scripts/databento/inspect_dbn.py`, `scripts/databento/import_trades.py`

ADR: [ADR-0014](../adr/ADR-0014-historical-archive-import-and-market-trade-storage.md)

### Derived OHLCV from trades (Phase 2B.3 — Sprint 012)

End-to-end flow:

```text
Published trades DatasetRef
  → derive_ohlcv_from_trades
  → TradesToBarsAggregator (1m UTC buckets)
  → validate → bars.parquet (single file)
  → lineage metadata → register WORKING   → finalize → publish
  → query_historical → list[MarketBar]  (boundary API)
  → query_historical_columnar → OhlcvColumnBatch  (batch research hot path)
```

CLI: `scripts/market_data/derive_bars_from_trades.py`

ADR: [ADR-0015](../adr/ADR-0015-derived-ohlcv-from-trades.md)

### Continuous futures materialization (Phase 2C.4 — Sprint 015)

End-to-end flow:

```text
Databento DBN (multi-contract)
  → import_databento_contract_trades_archive (split by actual_contract)
  → session_date-partitioned contract Parquet (NQ.NQM5, …)
  → build_roll_schedule (volume-rth-close, RTH session volumes)
  → materialize_continuous_trades (roll_id, is_roll_boundary)
  → derive_continuous_ohlcv (1m, same roll schedule)
  → finalize → publish
  → query_trades / query_historical (PUBLISHED only)
  → run_strategy_research (read-only consumer)
```

CLI: `scripts/market_data/build_continuous.py`, `scripts/market_data/batch_import_contract_trades_range.py`

ADR: [ADR-0018](../adr/ADR-0018-continuous-futures-materialization.md)

Deep reference: 📘 [modules/DATA_MODULE_UPDATED.md](modules/DATA_MODULE_UPDATED.md)

### `market/contracts/` · `market/continuous/` ✅ (Sprint 015)

| Package | Responsibility |
|---------|----------------|
| `market/contracts/` | Contract identity (`NQ.<CODE>`), `ContractTradeRecord`, session_date helpers, storage codec |
| `market/continuous/` | `RollPolicy`, `RollSchedule`, volume-RTH-close builder, materializer config, RTH volume aggregation |

### `market/` ✅

| | |
|---|---|
| **Responsibility** | Domain models: instrument, bar, **trade**, dataset identity, lifecycle, repository protocols |
| **Talks to** | `application/market_data`, `infrastructure/storage`, `market_analysis` (via `DatasetRef`, bars) |
| **Key paths** | `models/bar.py`, `models/trade.py`, `derivation/`, `datasets/identity.py`, `datasets/metadata.py`, `repositories/protocols.py`, `importers/archive.py`, `importers/trades_config.py` |
| **Public types** | `MarketBar`, `MarketTrade`, `TradeSide`, `DatasetRef`, `DatasetState`, `Instrument`, `ImportManifest`, `DerivedOhlcvFromTradesConfig`, `TradesToBarsAggregator` |

### `application/market_data/` ✅

| | |
|---|---|
| **Responsibility** | Dataset import, finalize, publish, historical query workflows (bars and trades) |
| **Talks to** | `market` domain, `infrastructure` adapters |
| **Key paths** | `import_external_dataset.py`, …, `query_historical.py`, `query_historical_columnar` (via `ohlcv_columnar.py`), `query_trades.py` |
| **Entry points** | `import_external_dataset`, …, `query_historical`, `query_historical_columnar`, `query_trades` |

### `infrastructure/` (market data slice) ✅

| Subpackage | Responsibility |
|------------|----------------|
| `importers/csv/` | CSV inspection and OHLCV import |
| `importers/databento/` | Databento DBN inspect, chunked/batch trades decode, contract split, storage normalizer |
| `normalization/` | UTC OHLCV normalizer |
| `validation/` | OHLCV and trade batch validators |
| `storage/parquet/` | Bar/trade Parquet; contract + continuous session partitions; roll schedule persistence |
| `storage/metadata/` | `FileDatasetRegistry`, contract dataset discovery |
| `storage/roll_schedule_repository.py` | Versioned roll schedule artifact |
| `storage/continuous_ohlcv_repository.py` | Partitioned continuous OHLCV read/write |
| `storage/import_manifest_store.py` | Persist/load `import_manifest.json` |
| `observability/` | Phase timing, RSS profiling for long preprocessing runs |

**Talks to:** `market` protocols only — not `market_analysis` or `strategy`.

---

## Market Analysis (Sprint 003–005) ✅

Engine, MTF foundation, CME ES RTH session enrichment and swing structure complete on sprint branch.
Built-in vertical slice components, frame assembler, `run_analysis` facade, Polars resample/align path
and MTF vertical slice are implemented.

Thin guide: [modules/MARKET_ANALYSIS_MODULE.md](modules/MARKET_ANALYSIS_MODULE.md)  
Binding decisions (vision): [../vision/MARKET_ANALYSIS_WITH_DECISIONS.md](../vision/MARKET_ANALYSIS_WITH_DECISIONS.md)  
Workspace design (vision): [../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md)

End-to-end flow (as implemented):

```text
Published DatasetRef (source timeframe, e.g. 1m)
  → run_analysis (application) or manual plan/execute
  → load_analysis_data_view → AnalysisDataView
  → RequestResolver.resolve_input_plan() → optional ResampleNode requirements
  → ComponentRegistry + DependencyPlanner → ExecutionPlan (components + ResampleNode)
  → SequentialBatchExecutor → AnalysisWorkspace (ResampleCache + ExecutionCache)
  → optional AnalysisFrameAssembler → AnalysisFrame (evaluation grid alignment)
  → optional TradingSessionMetadata (S005 session_resolver on run_analysis)
```

### `market_analysis/` ✅

| Subpackage | Status | Responsibility |
|------------|--------|----------------|
| `identity/` | ✅ | `ComponentId`, `ComputationIdentity`, `ResampleIdentity`, `AlignmentIdentity` |
| `models/` | ✅ | Requests, results, outputs, lineage, parameters, context, `ResampleSpec`, `AlignmentPolicy`, per-output `alignment_policy` |
| `protocols/` | ✅ | `BatchAnalysisComponent`, `ComponentImplementation` |
| `registry/` | ✅ | `ComponentRegistry`, `register_mvp_components` |
| `planning/` | ✅ | `RequestResolver`, `DependencyPlanner`, `ExecutionPlan`, `ResampleNode` |
| `data/` | ✅ | `AnalysisDataView`, `OhlcvColumnBatch`, Polars resample/align helpers |
| `storage/` | ✅ | `AnalysisResultStore`, `AnalysisWorkspace` |
| `execution/` | ✅ | `SequentialBatchExecutor`, `ExecutionCache`, `ResampleCache` |
| `adapters/numpy/` | ✅ | Indicator kernels and result builder (`available_at` on HTF) |
| `components/` | ✅ | TR, ATR, volatility state, EMA, `structure.swing` |
| `assembly/` | ✅ | `AnalysisFrameAssembler`, `AnalysisFrame`, `AlignmentCache`, optional session metadata |
| `errors.py` | ✅ | Analysis error hierarchy |

**Talks to:** `market` (via application), `time`, `core`. NumPy in adapters; Polars at resample/align boundary only.

### `application/market_analysis/` ✅

| | |
|---|---|
| **Responsibility** | Load market input and run end-to-end analysis |
| **Talks to** | `application/market_data`, `market_analysis` |
| **Key paths** | `load_data_view.py`, `run_analysis.py` |
| **Entry points** | `load_analysis_data_view`, `run_analysis` (supports `evaluation_timeframe`, MTF `ComponentRequest`, optional `session_resolver`) |

### `application/model_evaluation/` ✅

| | |
|---|---|
| **Responsibility** | `evaluate_models` orchestration, canonical examples |
| **Talks to** | `market_analysis`, `market_model`, `signal_model`, `model_expression` |
| **Key paths** | `evaluate_models.py`, `canonical_examples.py` |
| **Entry points** | `evaluate_models`, `build_canonical_model_bundle` |

### `application/signal_research/` ✅

| | |
|---|---|
| **Responsibility** | Signal Research run orchestration and read-only analytics |
| **Talks to** | `application/model_evaluation`, `strategy`, `research` |
| **Key paths** | `run_signal_research.py`, `analyze_signal_research.py` |
| **Entry points** | `run_signal_research`, `analyze_signal_research_run` |

### `application/strategy_research/` ✅

| | |
|---|---|
| **Responsibility** | Strategy Research run orchestration, read-only summary analytics and dashboard view model |
| **Talks to** | `application/model_evaluation`, `application/market_data`, `strategy`, `research` |
| **Key paths** | `run_strategy_research.py`, `analyze_strategy_research.py`, `dashboard.py`, `entry_signals.py`, `summarize.py` |
| **Entry points** | `run_strategy_research`, `analyze_strategy_research_run`, `build_strategy_dashboard_view_model`, `build_gated_entry_signals` |

---

## Declarative Models (Sprint 006) ✅

End-to-end flow:

```text
model_authoring DSL (optional)
  → compile → model_expression IR
  → evaluate_models
  → run_analysis once (deduplicated ComponentRequest set)
  → AnalysisFrame
  → MarketModelEvaluator / SignalModelEvaluator (+ firing)
```

### `model_expression/` ✅

| | |
|---|---|
| **Responsibility** | Operand references, expression AST, validation, Polars evaluation on `AnalysisFrame` |
| **Key paths** | `references.py`, `expressions.py`, `validation.py`, `evaluation/` |

### `model_authoring/` ✅

| | |
|---|---|
| **Responsibility** | User-facing typed references (`price`, `trend`, `volatility`, `structure`), conditions, `market_model` / `signal_model` builders |
| **Talks to** | `model_expression`, `market_model`, `signal_model` |
| **Entry points** | `market_model`, `signal_model`, `VolatilityState` |

### `market_model/` · `signal_model/` ✅

| Package | Responsibility |
|---------|----------------|
| `market_model/` | `MarketModelDefinition`, dense `model_result` evaluator |
| `signal_model/` | `SignalModelDefinition`, `SignalFiringPolicy`, sparse emissions |

---

## Signal Research (Sprint 008–010) ✅

End-to-end flow:

```text
Published DatasetRef
  → run_signal_research (scope-aware)
  → SignalOccurrence and/or MarketModelObservation facts
  → optional ContextFact (MARKET_AND_SIGNAL at available_at)
  → ForwardOutcome facts (long format)
  → immutable run envelope (manifest + scope-specific parquet tables)
  → analyze_signal_research_run (read-only aggregates)
  → optional HTML report (presentation-only)
```

ADR: [ADR-0011](../adr/ADR-0011-signal-research-outcomes-and-persistence.md),
[ADR-0012](../adr/ADR-0012-combined-research-scopes-and-context-alignment.md),
[ADR-0013](../adr/ADR-0013-signal-research-analytics-boundary.md)

## Strategy Research (Sprint 013–014) ✅

End-to-end flow:

```text
Published OHLCV DatasetRef
  → evaluate_models (shared evaluation table; Market × Signal)
  → build_gated_entry_signals
  → simulate_from_columnar (Numba kernel) or simulate (MarketBar path)
  → trades.parquet + equity.parquet + manifest
  → analyze_strategy_research_run (read-only summary)
  → build_strategy_dashboard_view_model (read-only inspection)
  → render_strategy_research_dashboard → standalone HTML (Phase A)
```

ADR: [ADR-0016](../adr/ADR-0016-ohlcv-strategy-research-mvp.md),
[ADR-0017](../adr/ADR-0017-strategy-research-inspection-boundary.md)

## Robustness Research (Sprint 016) ✅

End-to-end flow:

```text
RobustnessExperimentSpec (kinds + thresholds)
  → run_robustness_experiment / run_*_experiment (batch Strategy Research + resume)
  → analyze_*_experiment (read-only per kind)
  → analyze_robustness_experiment (verdict + report view model)
  → render_robustness_report → standalone HTML dashboard (Phase A)
```

ADR: [ADR-0019](../adr/ADR-0019-robustness-research-mvp.md)

### `research/robustness/` — Experiment contracts + analytics (Sprint 016) ✅

| | |
|---|---|
| **Responsibility** | Experiment spec, verdict thresholds, Monte Carlo / stress / WF analytics, HTML dashboard |
| **Key paths** | `experiment.py`, `verdict.py`, `report.py`, `report_html.py`, `analytics/` |
| **Entry points** | `run_robustness_experiment`, `analyze_robustness_experiment`, `render_robustness_experiment_report` |
| **Boundary** | Analytics read-only over persisted artifacts; stress/MC operate on trades (ADR-0019) |

### `research/analytics/` — Strategy dashboard (Sprint 014) ✅

| | |
|---|---|
| **Responsibility** | Dashboard view model types, KPI/panel metrics, HTML report renderer |
| **Key paths** | `strategy_dashboard.py`, `strategy_dashboard_metrics.py`, `strategy_dashboard_report.py`, `strategy_summarize.py` |
| **Entry points** | `compute_strategy_dashboard_analytics`, `render_strategy_research_dashboard` |
| **Boundary** | Presentation-only in report renderer; no Parquet I/O in renderer (ADR-0017) |

### `strategy/` ✅ (Signal Research + Strategy Research)

| | |
|---|---|
| **Responsibility** | `SignalOccurrence` materialization; Exit/Risk/Strategy model contracts (Sprint 013) |
| **Key paths** | `signal_occurrence.py`, `reference_price.py`, `exit_model.py`, `risk_model.py`, `strategy_model.py`, `canonical_examples.py` |
| **Entry points** | `materialize_signal_occurrences`, `build_canonical_strategy_model`, `validate_strategy_model_definition` |

### `research/` ✅ (Signal Research — Sprint 008–010; Strategy Research — Sprint 013)

| Subpackage | Responsibility |
|------------|----------------|
| `scope.py` | Explicit `ResearchScope` enum |
| `requests.py` | `SignalResearchRequest`, scope/model validation |
| `observations/` | `MarketModelObservation` TRUE_EDGE materialization |
| `context/` | `ContextFact` alignment at signal `available_at` |
| `outcomes/` | `ForwardOutcomeDefinition`, forward outcome calculator, OHLCV alignment |
| `datasets/` | Signal Research envelope (v1/v2); Strategy Research envelope (`strategy_research.v1`) |
| `simulation/` | `SimulationAssumptions`, `BarSequentialSimulator`, `compile_simulation_input_from_columnar`, Numba `fixed_bars` kernel, trade/equity fact schemas |
| `analytics/` | Read-only Signal Research analysis frame, RunSummary, grouping, optional HTML report |

**Entry points:** `validate_signal_research_request`, `run_signal_research`, `analyze_signal_research_run`,
`run_strategy_research`, `analyze_strategy_research_run`, `StrategyResearchDatasetRepository.read/write`,
`BarSequentialSimulator.simulate`, `BarSequentialSimulator.simulate_from_columnar`

### `core/profiling.py` ✅

Optional phase timing hooks (`optional_phase`) used across application and infrastructure for `--profile` CLIs.

### `scripts/demo/` ✅

| Script | Role |
|--------|------|
| `run_portfolio_demo.py` | Generate offline HTML portfolio bundle → `demo/output/` |

---

## Future Domains ⬜

| Package / track | Planned role |
|---------|----------------|
| `execution/` | Order execution domain (Execution Track — Phase 8+) |
| `events/` | Domain events |
| **Data Track 2B.2–2E** | Databento DBN OHLCV → `MarketBar`, quotes, options snapshots, live adapters (gated) — see `ROADMAP.md` §6 |
| **Research Track 4B, 6B** | Orderflow analysis, multi-data strategy simulation — see `ROADMAP.md` §10 |

Skeleton packages without public workflows beyond Signal Research slice above.

---

## Tests Mirror

| Area | Test location |
|------|----------------|
| Architecture boundary | `tests/unit/test_architecture_boundaries.py` |
| Market data integration | `tests/integration/market_data/` (CSV, mocked DBN trades, derived OHLCV from trades, Tier 2 Databento opt-in) |
| Continuous futures integration | `tests/integration/test_s015_continuous_strategy_research.py` |
| Continuous futures boundary | `tests/unit/test_continuous_futures_consumer_boundary.py` |
| Contract / continuous parquet | `tests/unit/infrastructure/test_contract_trade_repository.py`, `test_contract_rth_volumes.py`, `test_continuous_trades_to_ohlcv_table.py` |
| Databento unit tests | `tests/unit/infrastructure/databento/`, `tests/fixtures/databento/` |
| Databento CLI | `tests/unit/scripts/test_databento_cli.py` |
| Market analysis | `tests/unit/market_analysis/`, `tests/unit/application/market_analysis/`, `tests/integration/test_market_analysis_*` |
| Signal Research integration | `tests/integration/test_s008_run_signal_research.py`, `tests/integration/test_s009_*`, `tests/integration/test_s010_signal_research_analytics.py` |
| Strategy Research integration | `tests/integration/test_s013_run_strategy_research.py`, `tests/integration/test_s014_strategy_dashboard_view_model.py`, `tests/integration/test_s014_strategy_dashboard_report.py` |
| Strategy dashboard unit | `tests/unit/research/analytics/test_strategy_dashboard*.py` |
| Signal Research spikes | `tests/spike/run_combined_research_spike.py`, `tests/spike/run_inspect_combined_research.py`, `tests/spike/run_signal_research_analytics_spike.py`, `tests/spike/run_signal_research_analytics_report.py` |
| Signal Research unit | `tests/unit/strategy/`, `tests/unit/research/`, `tests/unit/application/signal_research/` |
| MA architecture boundaries | `tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py` |

---

## Maintenance

After each merged sprint wave, update status rows and flows in this file (5–10 lines per touched package).

After sprint closure, expand `reference/modules/` guides and align `vision/` if binding decisions changed.

Do not duplicate full contracts here — link to technical references and source.
