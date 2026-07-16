# Module Map

> **Reference doc** — [as-implemented layer](../README.md).  
> Data flows: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Research workflows: [RESEARCH_METHODOLOGIES.md](RESEARCH_METHODOLOGIES.md). Index: [docs/README.md](../README.md).

Package map for `src/trading_framework/`: responsibility, dependencies, status, entry points.

**Status legend:** ✅ implemented · 🟡 partial / in sprint · ⬜ skeleton · 📘 deep doc elsewhere

Last updated: 2026-07-15 (Sprint 017 complete on `sprint/model-research-methodology-mvp`; Sprint 016 on `main`)

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
infrastructure/       adapters — CSV, Parquet, file registry, Binance live feed
core/, time/, config/ shared primitives
strategy/, research/         Signal Research MVP (Sprint 008–010) ✅; Strategy Research MVP (Sprint 013) ✅; Strategy dashboard (Sprint 014) ✅
execution/                   🟡 dry-run contracts + local BTCUSDT runtime (Sprints 018-020)
events/                      ⬜ future domain events
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
| `providers/binance/` | Binance USD-M public live feed adapter, payload parsing, UTC mapping, reconnecting WebSocket client, smoke runner |

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
| **Responsibility** | Signal Research run orchestration, definition mapping, analytics persistence, HTML report rendering |
| **Talks to** | `application/model_evaluation`, `strategy`, `research` |
| **Key paths** | `run_signal_research.py`, `analyze_signal_research.py`, `map_definition.py`, `persist_analytics.py`, `render_signal_research_report.py`, `run_signal_research_family.py` |
| **Entry points** | `run_signal_research`, `analyze_signal_research_run`, `resolve_signal_research_definition`, `map_definition_to_run_request`, `persist_signal_research_analytics`, `render_signal_research_report`, `run_signal_research_family_experiment` |

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

## Model Research Methodology (Sprint 017) ✅

Phase 5B increment on Signal Research — declarative study contracts, quality diagnostics, Plotly
dashboard, production CLI, bounded model-family comparison, NQ half-year demo.

```text
SignalResearchDefinitionSpec (YAML/JSON)
  → resolve_signal_research_definition + map_definition_to_run_request
  → run_signal_research (bounded, lineage-recorded)
  → analyze_signal_research_run + SignalResearchQualityFlags
  → persist_signal_research_analytics (optional analytics/summary.json sidecar)
  → build_signal_research_report → offline Plotly HTML
  → optional run_signal_research_family_experiment (bounded variant comparison)
```

ADR: [ADR-0020](../adr/ADR-0020-model-research-methodology-mvp.md)

### `research/signal_research/` — Definition contracts (Sprint 017) ✅

| | |
|---|---|
| **Responsibility** | `SignalResearchDefinitionSpec`, occurrence policy, quality rules, model-family bounds |
| **Key paths** | `definition.py`, `loader.py`, `horizons.py`, `model_registry.py`, `family_planning.py` |
| **Entry points** | `load_signal_research_definition`, `validate_signal_research_definition`, `resolve_models_from_definition` |

### `research/reporting/signal_research/` — HTML dashboard (Sprint 017) ✅

| | |
|---|---|
| **Responsibility** | View models, Plotly figures, baseline comparison table, family comparison HTML |
| **Key paths** | `view_models.py`, `plotly_figures.py`, `report_html.py`, `family_report_html.py` |
| **Entry points** | `build_signal_research_report`, `build_family_comparison_report` |
| **Boundary** | Presentation-only; no model evaluation or Parquet I/O (ADR-0013, ADR-0020) |

### `research/analytics/quality_flags.py` — Quality diagnostics (Sprint 017) ✅

| | |
|---|---|
| **Responsibility** | Configurable warning flags (`LOW_SAMPLE_SIZE`, `HIGH_PERIOD_CONCENTRATION`, …) |
| **Entry points** | `compute_signal_research_quality_warnings` |

**CLI:** `scripts/signal_research/run_signal_research.py`, `analyze_signal_research.py`,
`render_signal_research_report.py`, `run_model_family.py`

**Demo:** `scripts/demo/run_model_research_nq_demo.py` → `demo/output/08_model_research_nq_half_year.html`

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

## Execution (Sprints 018-021 - Phase 8A local dry-run) 🟡

Sprint 018 introduced provider-independent **dry-run Execution contracts** for the BTC futures live-data
demo. Sprint 019 added provider-independent live market facts and a Binance adapter. Sprint 020 adds a
local BTCUSDT dry-run runtime loop using live Binance closed `kline_1m` bars and simulated broker
accounting. Sprint 021 adds a local execution state repository and latest-status read model for
operator inspection and future AWS/DynamoDB replacement.

```text
Binance BTCUSDT kline_1m WebSocket
  -> provider DTO parsing and mapping
  -> MarketBar
  -> rolling closed-bar history
  -> shared demo StrategyModelDefinition signal evaluation
  -> StrategyModelOrderAdapter
  -> PaperBroker
  -> JSONL execution events
  -> ExecutionStateRepository read model
```

ADR: [ADR-0021](../adr/ADR-0021-live-dry-run-execution-demo.md)

### `execution/` 🟡

| Subpackage / file | Status | Responsibility |
|-------------------|--------|----------------|
| `modes.py` | ✅ | `ExecutionMode.DRY_RUN`, supported-mode boundary |
| `safety.py` | ✅ | `ExecutionSafetyPolicy`, `DRY_RUN_SAFETY_POLICY`, no real orders / no credentials |
| `models/events.py` | ✅ | immutable `ExecutionEvent`, `ExecutionEventType` |
| `models/orders.py` | ✅ | `OrderIntent`, `SimulatedOrder`, `SimulatedFill`, dry-run order enums |
| `models/positions.py` | ✅ | `PaperPosition`, `PositionSide` |
| `models/account.py` | ✅ | `PaperAccountSnapshot` for paper equity / PnL reporting |
| `models/market_data.py` | ✅ | `BestBidAskSnapshot`, `MarketFeedStatusSnapshot`, `MarketFeedConnectionState` |
| `models/status.py` | ✅ | `Heartbeat`, `RuntimeStatusSnapshot`, `RuntimeHealth` |
| `protocols.py` | ✅ | read/event ports for future persistence and dashboard status |
| `broker_sim/` | ✅ | `PaperBroker`, simulated market fills, paper account/position accounting |
| `repositories/` | ✅ | `ExecutionStateRepository` ports and dashboard read-model contracts |
| `runtime/` | 🟡 | local session, decision step, signal adapter, closed-bar fill reference |

### `application/execution/` 🟡

| File | Status | Responsibility |
|------|--------|----------------|
| `local_btc_futures.py` | 🟡 | assemble local runtime, persist/read local state, restore paper broker state, run deterministic closed-bar and rolling feed steps |
| `binance_local_btc_futures.py` | 🟡 | map Binance messages into local dry-run feed state and bounded async loop |

### Execution persistence (Sprint 021)

Local operational state is stored by `JsonExecutionStateRepository` under an operator-provided path,
typically:

```text
user_data/runtime/btc_futures_dry_run/state/{runtime_id}/state.json
```

The state document contains the latest runtime status, latest paper account and position snapshots,
and bounded recent events/orders/fills. Default retention is 50 events, 20 orders and 20 fills.
`scripts/execution/show_execution_status.py` prints the latest read model as JSON. This read path is
inspection-only and does not expose runtime controls.

**CLI:**

```bash
uv run python scripts/execution/run_btc_futures_dry_run.py \
  --symbol BTCUSDT --duration-minutes 30

uv run python scripts/execution/show_execution_status.py \
  --state-repository user_data/runtime/btc_futures_dry_run/state \
  --runtime-id btc-futures-dry-run-local
```

Operator notes: [LOCAL_BTC_FUTURES_DRY_RUN.md](LOCAL_BTC_FUTURES_DRY_RUN.md)

**Boundary:** all orders, fills, positions and PnL in this increment are simulated. `execution/` must not
import `research`, concrete `infrastructure` or `user_data`. Provider payload schemas are not execution
contracts; they stay under `infrastructure/providers/binance/`.

**Tests:** `tests/unit/execution/`

---

## Binance Live Feed Adapter (Sprint 019 - Phase 8A) ✅

The Binance adapter is an infrastructure boundary for public BTCUSDT USD-M futures market data.
It does not read account credentials, place orders or expose Binance payload schemas to runtime
consumers.

| File | Status | Responsibility |
|------|--------|----------------|
| `providers/binance/futures_streams.py` | ✅ | routed stream specs, `/market` and `/public` combined-stream URLs |
| `providers/binance/futures_payloads.py` | ✅ | provider DTO parsing for combined/raw `kline_1m` and `bookTicker` payloads |
| `providers/binance/futures_mapper.py` | ✅ | provider DTOs -> `MarketBar` and `BestBidAskSnapshot` |
| `providers/binance/futures_reconnect.py` | ✅ | bounded exponential reconnect policy |
| `providers/binance/futures_websocket.py` | ✅ | transport-agnostic reconnecting WebSocket client |
| `providers/binance/aiohttp_websocket.py` | ✅ | concrete `aiohttp` WebSocket transport adapter |
| `providers/binance/futures_smoke.py` | ✅ | bounded smoke runner and smoke JSON normalization |
| `scripts/live_data/run_binance_futures_smoke.py` | ✅ | local BTCUSDT smoke CLI |

**Smoke CLI:**

```bash
uv run python scripts/live_data/run_binance_futures_smoke.py \
  --symbol BTCUSDT --duration-seconds 10 --max-messages 20
```

**Tests:** `tests/unit/infrastructure/binance/`, `tests/unit/scripts/test_binance_futures_smoke_cli.py`,
`tests/integration/live_data/test_binance_futures_network_smoke.py` (opt-in network).

---

## Future Domains ⬜

| Package / track | Planned role |
|---------|----------------|
| `events/` | Domain events |
| **Execution Track 8A.2+** | persistence/read model, AWS runtime, OVH dashboard — see Sprints 021–025 |
| **Data Track 2B.2–2E** | Databento DBN OHLCV → `MarketBar`, quotes, options snapshots, live adapters (gated) — see `ROADMAP.md` §6 |
| **Research Track 4B, 6B** | Orderflow analysis, multi-data strategy simulation — see `ROADMAP.md` §10 |

`events/` remains a skeleton package. Execution has local dry-run runtime support; durable read models,
AWS deployment and the public dashboard begin in later Phase 8A sprints.

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
| Execution contracts | `tests/unit/execution/test_dry_run_contracts.py` |
| Execution architecture boundaries | `tests/unit/execution/test_execution_architecture_boundaries.py` |
| Binance live feed adapter | `tests/unit/infrastructure/binance/`, `tests/integration/live_data/test_binance_futures_network_smoke.py` (opt-in) |
| Local BTC futures dry-run | `tests/unit/application/execution/`, `tests/unit/scripts/test_btc_futures_dry_run_cli.py` |
| Execution read model persistence | `tests/unit/execution/repositories/`, `tests/unit/infrastructure/storage/test_execution_state_repository.py`, `tests/unit/scripts/test_show_execution_status_cli.py` |

---

## Maintenance

After each merged sprint wave, update status rows and flows in this file (5–10 lines per touched package).

After sprint closure, expand `reference/modules/` guides and align `vision/` if binding decisions changed.

Do not duplicate full contracts here — link to technical references and source.
