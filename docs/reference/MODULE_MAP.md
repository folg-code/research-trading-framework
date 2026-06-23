# Module Map

> **Reference doc** — [as-implemented layer](../README.md).  
> Data flows: [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md). Index: [docs/README.md](../README.md).

Package map for `src/trading_framework/`: responsibility, dependencies, status, entry points.

**Status legend:** ✅ implemented · 🟡 partial / in sprint · ⬜ skeleton · 📘 deep doc elsewhere

Last updated: 2026-06-23 (Sprint 003, Waves 0–3 merged)

---

## Layer Overview

```text
application/          use cases — orchestrates domain + infrastructure
    ↓ uses
market/               market domain models and repository protocols
market_analysis/      analysis domain — components, planning, execution
infrastructure/       adapters — CSV, Parquet, file registry
core/, time/, config/ shared primitives
strategy/, research/, execution/, events/   ⬜ future domains
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
| **Responsibility** | UTC instants, timeframes, `Clock` protocol |
| **Talks to** | `market`, `market_analysis` (time ranges) |
| **Key paths** | `models/utc_instant.py`, `models/timeframe.py`, `clocks/` |

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

## Market Analysis (Sprint 003) 🟡

Engine scaffold through Wave 3. Vertical slice components, frame assembler and public facade are **not yet** implemented.

Thin guide: [modules/MARKET_ANALYSIS_MODULE.md](modules/MARKET_ANALYSIS_MODULE.md)  
Binding decisions (vision): [../vision/MARKET_ANALYSIS_WITH_DECISIONS.md](../vision/MARKET_ANALYSIS_WITH_DECISIONS.md)  
Workspace design (vision): [../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md)

End-to-end flow (as implemented):

```text
Published DatasetRef
  → load_analysis_data_view (application)
  → query_historical → AnalysisDataView
  → ComponentRegistry + DependencyPlanner → ExecutionPlan
  → SequentialBatchExecutor
  → AnalysisResultStore / AnalysisWorkspace
```

Not yet wired: `AnalysisFrameAssembler`, `run_analysis` facade, built-in TR/ATR/EMA components.

### `market_analysis/` 🟡

| Subpackage | Status | Responsibility |
|------------|--------|----------------|
| `identity/` | ✅ | `ComponentId`, `ComputationIdentity`, versions |
| `models/` | ✅ | Requests, results, outputs, lineage, parameters, context |
| `protocols/` | ✅ | `BatchAnalysisComponent`, `ComponentImplementation` |
| `registry/` | ✅ | `ComponentRegistry` |
| `planning/` | ✅ | `DependencyPlanner`, `ExecutionPlan`, cycle detection |
| `data/` | ✅ | `AnalysisDataView` — read-only OHLCV columns (`float64` in view) |
| `storage/` | ✅ | `AnalysisResultStore`, `AnalysisWorkspace`, `AnalysisWorkspaceView` |
| `execution/` | ✅ | `SequentialBatchExecutor`, `ExecutionCache`, warmup helpers |
| `errors.py` | ✅ | Analysis error hierarchy |
| components (TR, ATR, EMA, …) | ⬜ | Wave 4 |
| frame assembly | ⬜ | Wave 4 (`AnalysisFrameAssembler`) |
| engine facade | ⬜ | Wave 4 |

**Talks to:** `market` (`DatasetRef` indirectly via application), `time`, `core`. Does **not** import pandas in public API.

### `application/market_analysis/` 🟡

| | |
|---|---|
| **Responsibility** | Bridge published datasets into analysis input |
| **Talks to** | `application/market_data.query_historical`, `AnalysisDataView` |
| **Key paths** | `load_data_view.py` |
| **Entry point** | `load_analysis_data_view` |

---

## Future Domains ⬜

| Package | Planned role |
|---------|----------------|
| `strategy/` | Stateless strategy definitions |
| `research/` | Research workflows, experiment tracking |
| `execution/` | Order execution domain (not `market_analysis/execution`) |
| `events/` | Domain events |

Skeleton `__init__.py` only — no public workflows.

---

## Tests Mirror

| Area | Test location |
|------|----------------|
| Architecture boundary | `tests/unit/test_architecture_boundaries.py` |
| Market data integration | `tests/integration/market_data/` |
| Market analysis | `tests/unit/market_analysis/`, `tests/unit/application/market_analysis/` |
| MA architecture boundaries | `tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py` |

---

## Maintenance

After each merged sprint wave, update status rows and flows in this file (5–10 lines per touched package).

After sprint closure, expand `reference/modules/` guides and align `vision/` if binding decisions changed.

Do not duplicate full contracts here — link to technical references and source.
