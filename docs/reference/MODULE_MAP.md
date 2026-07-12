# Module Map

> **Reference doc** — [as-implemented layer](../README.md).  
> Data flows: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Index: [docs/README.md](../README.md).

Package map for `src/trading_framework/`: responsibility, dependencies, status, entry points.

**Status legend:** ✅ implemented · 🟡 partial / in sprint · ⬜ skeleton · 📘 deep doc elsewhere

Last updated: 2026-07-12 (Sprint 008 complete)

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
strategy/, research/         Signal Research MVP (Sprint 008) ✅ / 🟡
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

## Market Data (Sprint 002) ✅

End-to-end flow:

```text
CSV file
  → import_external_dataset
  → normalize (UTC OHLCV)
  → validate
  → Parquet write
  → register in FileDatasetRegistry
  → finalize_dataset → publish_dataset
  → query_historical → list[MarketBar]
```

Deep reference: 📘 [modules/DATA_MODULE_UPDATED.md](modules/DATA_MODULE_UPDATED.md)

### `market/` ✅

| | |
|---|---|
| **Responsibility** | Domain models: instrument, bar, dataset identity, lifecycle, repository protocols |
| **Talks to** | `application/market_data`, `infrastructure/storage`, `market_analysis` (via `DatasetRef`, bars) |
| **Key paths** | `models/bar.py`, `datasets/identity.py`, `datasets/metadata.py`, `repositories/protocols.py` |
| **Public types** | `MarketBar`, `DatasetRef`, `DatasetState`, `Instrument` |

### `application/market_data/` ✅

| | |
|---|---|
| **Responsibility** | Dataset import, finalize, publish, historical query workflows |
| **Talks to** | `market` domain, `infrastructure` adapters |
| **Key paths** | `import_external_dataset.py`, `finalize_dataset.py`, `publish_dataset.py`, `query_historical.py` |
| **Entry points** | `import_external_dataset`, `finalize_dataset`, `publish_dataset`, `query_historical` |

### `infrastructure/` (market data slice) ✅

| Subpackage | Responsibility |
|------------|----------------|
| `importers/csv/` | CSV inspection and OHLCV import |
| `normalization/` | UTC OHLCV normalizer |
| `validation/` | OHLCV validator |
| `storage/parquet/` | Parquet read/write (`Decimal` prices as string in storage) |
| `storage/metadata/` | `FileDatasetRegistry` |

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
| **Responsibility** | Signal Research run orchestration (`SIGNAL_MODEL_ONLY` MVP) |
| **Talks to** | `application/model_evaluation`, `strategy`, `research` |
| **Key paths** | `run_signal_research.py` |
| **Entry points** | `run_signal_research` |

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

## Signal Research (Sprint 008) ✅

End-to-end flow:

```text
Published DatasetRef
  → run_signal_research (or evaluate_models + materialization + outcomes)
  → SignalOccurrence facts
  → ForwardOutcome facts (long format)
  → immutable run envelope (manifest + occurrences.parquet + outcomes.parquet)
  → repository read / inspection spike
```

ADR: [ADR-0011](../adr/ADR-0011-signal-research-outcomes-and-persistence.md)

### `strategy/` ✅ (Signal Research slice)

| | |
|---|---|
| **Responsibility** | `SignalOccurrence` materialization, reference-price policy |
| **Key paths** | `signal_occurrence.py`, `reference_price.py` |
| **Entry points** | `materialize_signal_occurrences`, `derive_occurrence_id`, `resolve_reference_price` |

### `research/` ✅ (Signal Research slice)

| Subpackage | Responsibility |
|------------|----------------|
| `outcomes/` | `ForwardOutcomeDefinition`, forward outcome calculator, OHLCV alignment |
| `datasets/` | Run envelope manifest, `SignalResearchDatasetRepository`, deterministic `run_id` |

**Entry points:** `compute_forward_outcomes`, `compute_forward_outcomes_for_horizons`,
`SignalResearchDatasetRepository.read/write`

---

## Future Domains ⬜

| Package | Planned role |
|---------|----------------|
| `execution/` | Order execution domain (not `market_analysis/execution`) |
| `events/` | Domain events |

Skeleton packages without public workflows beyond Signal Research slice above.

---

## Tests Mirror

| Area | Test location |
|------|----------------|
| Architecture boundary | `tests/unit/test_architecture_boundaries.py` |
| Market data integration | `tests/integration/market_data/` |
| Market analysis | `tests/unit/market_analysis/`, `tests/unit/application/market_analysis/`, `tests/integration/test_market_analysis_*` |
| Signal Research integration | `tests/integration/test_s008_run_signal_research.py` |
| Signal Research unit | `tests/unit/strategy/`, `tests/unit/research/` |
| MA architecture boundaries | `tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py` |

---

## Maintenance

After each merged sprint wave, update status rows and flows in this file (5–10 lines per touched package).

After sprint closure, expand `reference/modules/` guides and align `vision/` if binding decisions changed.

Do not duplicate full contracts here — link to technical references and source.
