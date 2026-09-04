# Trading Research Framework

# DATA_MODULE.md

> **As-implemented reference.** This file was reclassified from a
> Sprint-002-era mixed vision/reference document by the follow-up to
> Sprint 054 T007 (see
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` for the section-by-section
> classification). It now contains only content confirmed CURRENT against
> the codebase. Target-architecture / not-yet-built content was moved to
> `docs/vision/DATA_MODULE_FUTURE.md`. Cross-cutting package/responsibility
> information already covered by `docs/reference/system/MODULE_MAP.md` §5
> "Market Data Implementation Map" is not duplicated here — see that
> document for packages, dependency direction, and test paths.

## 1. Purpose

This document defines the architecture, responsibilities, workflows and implementation rules of the Market Data Module.

It translates the system-level architecture into a concrete contract for:

- market data models,
- market dataset lifecycle,
- historical data synchronization,
- external dataset imports,
- local historical data access,
- live data ingestion,
- live data recording,
- partition finalization,
- dataset publication,
- historical replay,
- storage layout,
- futures contract data,
- continuous futures data,
- raw data retention,
- validation,
- missing range detection,
- provider and storage boundaries.

This document must be read together with:

- `ARCHITECTURE_FOUNDATIONS.md`,
- `ARCHITECTURE_TECHNICAL.md`,
- `WORKFLOWS_AI_ADR.md`.

The Market Data Module is shared by:

```text
Signal Research
Strategy Research
Strategy Execution
```

These capabilities may consume the same market data contracts, but they use different application workflows.

---

## 3. Domain Ownership

The Market Domain owns:

- `Instrument`,
- `MarketBar`,
- `MarketTrade`,
- `MarketQuote`,
- market data identifiers,
- market dataset definitions,
- dataset metadata,
- dataset lifecycle state,
- provider contracts,
- importer contracts,
- normalization contracts,
- validation contracts,
- repository contracts,
- market data access contracts.

The Market Domain does not own:

- Market Analysis components,
- market interpretation,
- market regimes,
- signals,
- exits,
- risk models,
- strategies,
- research analytics,
- backtesting logic,
- broker order execution.

Application workflows coordinate Market Domain contracts.

Concrete providers, importers and storage adapters belong to infrastructure.

> Note: `MarketQuote` is listed above per the original architecture text but
> is not yet implemented (see `docs/planning/DATA_MODULE_CLASSIFICATION.md`
> §3/§6). Everything else in this ownership list is built.

---

## 4. Architectural Layers

The Market Data Module is divided into three conceptual layers.

### 4.1 Domain and Contracts

Contains:

- immutable market models,
- dataset models,
- requests and queries,
- provider Protocols,
- importer Protocols,
- repository Protocols,
- validation contracts,
- normalization contracts.

Suggested location:

```text
src/trading_framework/market/
```

### 4.2 Application Workflows

Contains use-case orchestration:

- historical synchronization,
- external dataset import,
- local historical query,
- live data ingestion,
- live recording,
- partition finalization,
- dataset publication,
- historical replay.

Suggested location:

```text
src/trading_framework/application/market_data/
```

### 4.3 Infrastructure Adapters

Contains concrete implementations:

- Databento,
- Rithmic,
- Binance,
- MetaTrader 5,
- CSV readers,
- DBN readers,
- Parquet repositories,
- DuckDB query adapters,
- live storage writers.

Suggested location:

```text
src/trading_framework/infrastructure/
```

The domain and application layers must not depend on provider SDKs, file format libraries or storage drivers directly.

---

## 5. Core Principles

### 5.2 Research Must Be Reproducible

Research and backtesting should consume explicit, published dataset versions.

A research workflow must not silently download or mutate market data during computation.

Preferred flow:

```text
Data Preparation
      ↓
Published DatasetRef
      ↓
Research Run
```

If a research request requires missing data, synchronization must be an explicit preparation step or an explicitly configured precondition.

---

### 5.3 Provider Schemas Must Not Leak

Provider-specific fields, enums and SDK objects must be normalized at the infrastructure boundary.

Correct:

```text
Provider DTO
    ↓
Normalizer
    ↓
MarketBar / MarketTrade / MarketQuote
```

Incorrect:

```text
Research Logic
    ↓
Provider SDK Object
```

---

### 5.4 Storage Is Not the Domain Model

A market dataset is not a file path.

It has:

- identity,
- version,
- source,
- coverage,
- data type,
- timeframe,
- schema,
- validation status,
- lifecycle state,
- checksum,
- lineage.

Parquet is a storage implementation around that model.

---

### 5.7 Futures Contracts and Storage Partitions Are Separate Concepts

A futures contract is a semantic dataset dimension.

A storage partition is a physical organization mechanism.

The framework must not assume:

```text
calendar quarter = futures contract lifecycle
```

Raw futures contract data must preserve the actual contract symbol, for example:

```text
NQH26
NQM26
NQU26
NQZ26
```

Continuous futures data is a derived dataset with explicit roll lineage.

---

## 6. Market Data Model Invariants

> The canonical/future model list this section originally led with (which
> Model types exist vs. are planned) moved to
> `docs/vision/DATA_MODULE_FUTURE.md` §6 — see
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` for why. The general
> modeling rules below apply to whichever market fact models exist today
> (`Instrument`, `MarketBar`, `MarketTrade`).

Each market fact should:

- use timezone-aware UTC timestamps internally,
- be immutable where practical,
- be provider-independent,
- preserve stable instrument identity,
- use explicit numeric types,
- define invariants.

Example `MarketBar` invariants:

```text
high >= open
high >= close
low <= open
low <= close
high >= low
volume >= 0
```

Bars are independent observations.

A bar may be:

- supplied directly by a provider,
- aggregated from trades,
- aggregated from quotes,
- imported from a local archive.

The source and construction method belong to dataset metadata.

---

## 7. Dataset Model

A dataset is a versioned collection of market facts with a stable identity.

Suggested metadata:

```text
dataset_id
version
provider
source_id
asset_class
instrument_id
contract_id
data_type
timeframe
start_at
end_at
timezone
calendar_id
schema_version
normalization_version
validation_status
lifecycle_status
checksum
row_count
source_checksum
created_at
published_at
lineage
```

Not every field applies to every data type.

For example, `timeframe` may be absent for individual trades.

### 7.1 Dataset Identity

A material change creates a new dataset version.

Material changes include:

- changed source data,
- corrected records,
- changed normalization logic,
- changed symbol mapping,
- changed calendar assumptions,
- changed roll policy,
- changed adjustment method,
- changed schema semantics.

A file rewrite that preserves identical logical content does not necessarily create a new logical version.

### 7.2 Dataset Reference

Consumers should use a stable reference such as:

```text
DatasetRef(dataset_id, version)
```

Research must record the exact reference used.

---

## 8. Dataset Lifecycle

Suggested dataset states:

```text
WORKING
FINALIZED
PUBLISHED
INVALID
SUPERSEDED
```

### WORKING

Dataset or partition is still receiving data or being transformed.

It may change.

It must not be treated as a reproducible research input.

### FINALIZED

The current content has been:

- ordered,
- deduplicated,
- validated,
- checksummed,
- closed for normal writes.

### PUBLISHED

The dataset version is available as a stable input for research or replay.

### INVALID

The dataset failed validation or has known integrity problems.

### SUPERSEDED

A newer version replaces it for normal use.

The old version may remain available for historical reproducibility.

---

## 11. External Dataset Import

### 11.1 Purpose

External import handles files delivered outside a provider API.

Examples:

- Databento DBN,
- CSV,
- Parquet,
- compressed vendor archives,
- broker exports,
- archived tick files.

### 11.2 Workflow

```text
External Source
    ↓
Inspect
    ↓
Resolve Import Configuration
    ↓
Read Source
    ↓
Map Provider Schema
    ↓
Normalize
    ↓
Validate
    ↓
Partition
    ↓
Persist Canonical Dataset
    ↓
Register Dataset Version
```

### 11.3 Inspect Before Import

The importer should support an inspection phase that identifies:

- source format,
- source checksum,
- available instruments,
- contract symbols,
- data type,
- schema,
- source timezone,
- time range,
- estimated rows,
- compression,
- warnings,
- unsupported fields.

Import should not begin by guessing these properties silently.

### 11.4 API Provider and File Importer Are Different Contracts

Examples:

```text
DatabentoHistoricalProvider
DatabentoDBNImporter
```

They may share normalization code, but they represent different use cases.

---

## 12. Local Historical Data Access

### 12.1 Purpose

Research and backtesting query published local datasets through repository contracts.

### 12.2 Workflow

```text
MarketDataQuery
    ↓
Resolve DatasetRef
    ↓
Check Publication and Validation Status
    ↓
Select Relevant Partitions
    ↓
Apply Column Projection
    ↓
Apply Time Filter
    ↓
Return MarketDataBatch or Lazy View
```

### 12.3 Rules

- Consumers must not discover Parquet paths themselves.
- Consumers must not open storage files directly.
- Research should use published dataset versions.
- Queries should support partition pruning.
- Queries should read only required columns.
- The repository may use Polars or DuckDB internally.
- Public contracts should not make storage format assumptions unnecessarily.

---

## 15. Partition Finalization

Finalization converts working ingestion data into stable canonical partitions.

### 15.1 Workflow

```text
Working Files
    ↓
Load Relevant Partition
    ↓
Normalize Remaining Fields
    ↓
Sort
    ↓
Deduplicate
    ↓
Validate
    ↓
Compact
    ↓
Write Final Partition
    ↓
Checksum
    ↓
Update Dataset Metadata
    ↓
Mark FINALIZED
```

Finalization performs:

```text
WORKING → FINALIZED
```

It does not publish the dataset automatically.

### 15.2 Rules

- Finalization must be idempotent where possible.
- Source working files must not be deleted before successful validation and durable final write.
- Failed finalization must leave recoverable state.
- Finalized partitions should normally be immutable.
- A corrected finalized partition creates a new dataset version.

---

## 16. Dataset Publication

Publication exposes a finalized dataset version as a stable input for Research or Replay Execution.

### 16.1 Workflow

```text
FINALIZED Dataset Version
    ↓
Verify Finalization Metadata
    ↓
Verify Validation Status
    ↓
Freeze Logical Version
    ↓
Register Publication Metadata
    ↓
Mark PUBLISHED
```

Publication performs:

```text
FINALIZED → PUBLISHED
```

`finalize()` and `publish()` are separate use cases.

A convenience workflow such as `finalize_and_publish()` may call both, but it must record both transitions explicitly.

A `PUBLISHED` dataset version is immutable.

---

## 18. Storage Architecture

### 18.1 Primary Format

Apache Parquet is the primary format for historical analytical market data.

Reasons:

- columnar storage,
- compression,
- predicate pushdown,
- projection pushdown,
- Polars support,
- DuckDB support,
- low infrastructure overhead.

### 18.3 Suggested User Layout

Canonical workspace (``--storage-root`` = ``user_data/``):

```text
user_data/
├── market_data/
│   ├── raw/           # vendor archives (immutable)
│   ├── metadata/      # dataset registry JSON
│   ├── normalized/    # published Parquet market facts
│   └── continuous/    # roll schedules
├── research/
│   ├── market_research/
│   ├── strategy_research/
│   ├── strategy_robustness/
│   └── predictive_research/   # datasets/{dataset_id}/ (Phase 10A)
└── runtime/
```

Do not create ad-hoc top-level ``storage_*`` roots for new work. Migrate legacy trees with
``scripts/ops/migrate_user_data_workspace.py``.

---

## 20. Futures Contract Data

### 20.1 Contract Identity

Raw or normalized futures data must preserve the actual contract identity.

Example:

```text
root_symbol = NQ
contract_symbol = NQM26
expiration_month = 2026-06
```

A contract dataset must not be identified only as `NQ`.

---

## 23. Validation

Validation is separated into stages.

### 23.1 Import or Batch Validation

Checks:

- schema,
- required fields,
- numeric types,
- timestamps,
- instrument mapping,
- source metadata.

### 23.3 Final Dataset Validation

Checks:

- ordering,
- duplicates,
- gaps,
- expected sessions,
- holidays,
- OHLC invariants,
- volume rules,
- partition boundaries,
- metadata consistency,
- checksum,
- row counts.

---

## 27. Prohibited Designs

The following designs are prohibited.

### God-Object Data Manager

Do not create one class that owns:

- provider access,
- missing range calculation,
- normalization,
- validation,
- storage,
- research queries,
- live streaming,
- replay.

### Research-Triggered Hidden Downloads

Research must not silently call an external provider and mutate its input dataset.

### Direct File Access From Research or Strategy

Research and Strategy components must not open Parquet files directly.

### Provider Objects in Domain Logic

Provider SDK objects must not cross the adapter boundary.

### Mutable Published Dataset

A published dataset version must not change in place.

### Continuous Futures Without Lineage

A continuous series without recorded roll and adjustment policy is invalid.

### One File Per Live Event

Live ingestion must use batching and compaction.

### Permanent Raw Duplication by Default

The framework must not automatically store full raw and normalized copies for every dataset.

### Futures Quarter Assumption

The framework must not equate calendar quarters with actual contract lifecycle or roll boundaries.
