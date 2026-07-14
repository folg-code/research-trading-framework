# Module Map

> **Reference doc** — [as-implemented layer](../README.md).  
> Data flows: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Index: [docs/README.md](../README.md).

Package map for `src/trading_framework/`: responsibility, dependencies, status, entry points.

**Status legend:** ✅ implemented · 🟡 partial / in sprint · ⬜ skeleton · 📘 deep doc elsewhere

Last updated: 2026-07-14 (Sprint 012 complete on `sprint/trades-to-ohlcv-derived`; Phase 2B.3 derived OHLCV from trades)

**Roadmap:** parallel capability tracks and phase families — `docs/planning/ROADMAP.md` §3. Sprint 002 delivered Phase 2A (OHLCV only). Sprint 011 delivered Phase 2B + 2C.1 (Databento trades). Sprint 012 delivered Phase 2B.3 (derived 1m bars from trades).

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
strategy/, research/         Signal Research MVP (Sprint 008–010) ✅
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

## Market Data (Sprint 002 — Phase 2A; Sprint 011 — Phase 2B + 2C.1; Sprint 012 — Phase 2B.3) ✅

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
  → query_historical → list[MarketBar]
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
  → lineage metadata → register WORKING → finalize → publish
  → query_historical → list[MarketBar]
```

CLI: `scripts/market_data/derive_bars_from_trades.py`

ADR: [ADR-0015](../adr/ADR-0015-derived-ohlcv-from-trades.md)

Deep reference: 📘 [modules/DATA_MODULE_UPDATED.md](modules/DATA_MODULE_UPDATED.md)

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
| **Key paths** | `import_external_dataset.py`, `import_databento_trades_archive.py`, `derive_ohlcv_from_trades.py`, `finalize_dataset.py`, `publish_dataset.py`, `query_historical.py`, `query_trades.py` |
| **Entry points** | `import_external_dataset`, `import_databento_trades_archive`, `derive_ohlcv_from_trades`, `finalize_dataset`, `publish_dataset`, `query_historical`, `query_trades` |

### `infrastructure/` (market data slice) ✅

| Subpackage | Responsibility |
|------------|----------------|
| `importers/csv/` | CSV inspection and OHLCV import |
| `importers/databento/` | Databento DBN inspect, chunked trades decode, row mapping |
| `normalization/` | UTC OHLCV normalizer |
| `validation/` | OHLCV and trade batch validators |
| `storage/parquet/` | Bar and trade Parquet read/write; day-partitioned trade repository |
| `storage/metadata/` | `FileDatasetRegistry` |
| `storage/import_manifest_store.py` | Persist/load `import_manifest.json` |

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
| `data/` | ✅ | `AnalysisDataView`, Polars resample/align helpers |
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

### `strategy/` ✅ (Signal Research slice)

| | |
|---|---|
| **Responsibility** | `SignalOccurrence` materialization, reference-price policy |
| **Key paths** | `signal_occurrence.py`, `reference_price.py` |
| **Entry points** | `materialize_signal_occurrences`, `derive_occurrence_id`, `resolve_reference_price` |

### `research/` ✅ (Signal Research — Sprint 008–010)

| Subpackage | Responsibility |
|------------|----------------|
| `scope.py` | Explicit `ResearchScope` enum |
| `requests.py` | `SignalResearchRequest`, scope/model validation |
| `observations/` | `MarketModelObservation` TRUE_EDGE materialization |
| `context/` | `ContextFact` alignment at signal `available_at` |
| `outcomes/` | `ForwardOutcomeDefinition`, forward outcome calculator, OHLCV alignment |
| `datasets/` | Run envelope manifest (v1/v2), `SignalResearchDatasetRepository`, `derive_run_id` / `derive_run_id_v2` |
| `analytics/` | Read-only analysis frame, RunSummary, grouping, conditional comparison, optional HTML report |

**Entry points:** `validate_signal_research_request`, `materialize_market_model_observations`,
`align_context_facts_at_available_at`, `compute_forward_outcomes`,
`SignalResearchDatasetRepository.read/write`, `run_signal_research`,
`build_analysis_frame`, `analyze_signal_research_run`, `render_signal_research_report`

---

## Future Domains ⬜

| Package / track | Planned role |
|---------|----------------|
| `execution/` | Order execution domain (Execution Track — Phase 8+) |
| `events/` | Domain events |
| **Data Track 2B.2–2E** | Databento DBN OHLCV → `MarketBar`, quotes, options snapshots, live adapters (gated) — see `ROADMAP.md` §6 |
| **Research Track 4B, 6A–6B** | Orderflow analysis, OHLCV Strategy Research, multi-data simulation — see `ROADMAP.md` §10 |

Skeleton packages without public workflows beyond Signal Research slice above.

---

## Tests Mirror

| Area | Test location |
|------|----------------|
| Architecture boundary | `tests/unit/test_architecture_boundaries.py` |
| Market data integration | `tests/integration/market_data/` (CSV, mocked DBN trades, derived OHLCV from trades, Tier 2 Databento opt-in) |
| Databento unit tests | `tests/unit/infrastructure/databento/`, `tests/fixtures/databento/` |
| Databento CLI | `tests/unit/scripts/test_databento_cli.py` |
| Market analysis | `tests/unit/market_analysis/`, `tests/unit/application/market_analysis/`, `tests/integration/test_market_analysis_*` |
| Signal Research integration | `tests/integration/test_s008_run_signal_research.py`, `tests/integration/test_s009_*`, `tests/integration/test_s010_signal_research_analytics.py` |
| Signal Research spikes | `tests/spike/run_combined_research_spike.py`, `tests/spike/run_inspect_combined_research.py`, `tests/spike/run_signal_research_analytics_spike.py`, `tests/spike/run_signal_research_analytics_report.py` |
| Signal Research unit | `tests/unit/strategy/`, `tests/unit/research/`, `tests/unit/application/signal_research/` |
| MA architecture boundaries | `tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py` |

---

## Maintenance

After each merged sprint wave, update status rows and flows in this file (5–10 lines per touched package).

After sprint closure, expand `reference/modules/` guides and align `vision/` if binding decisions changed.

Do not duplicate full contracts here — link to technical references and source.
