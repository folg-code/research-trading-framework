# Trading Research Framework

# DATA_MODULE.md

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

## 2. Scope

The Market Data Module is responsible for providing trusted, normalized, versioned and reproducible market facts.

It supports:

- historical provider APIs,
- live provider streams,
- externally supplied files,
- local datasets,
- market data normalization,
- market data validation,
- storage and retrieval,
- dataset metadata,
- missing range resolution,
- futures contract datasets,
- derived continuous futures datasets,
- historical replay.

The module must support providers that expose different data granularities, including:

```text
Bars
Trades
Quotes
Order Book Updates
DOM Snapshots
Other provider-specific market facts
```

The architecture must not assume that every provider exposes all data types.

### Roadmap alignment (2026-07-12)

Market Data development follows the **Data Capability Track** in `ROADMAP.md`:

```text
Phase 2A — OHLCV Market Data MVP              COMPLETE (Sprint 002)
Phase 2B — Historical Archive Import Foundation   PLANNED (Databento DBN first)
Phase 2C — Trades and Quotes                      PLANNED (MarketTrade, MarketQuote)
Phase 2D — Options Snapshot Data                  PLANNED
Phase 2E — Live Market Data                       GATED
```

Phase 2A delivered CSV/Parquet OHLCV import only. Archive import, tick facts, options snapshots and live adapters are separate increments. Canonical trade/quote models are **`MarketTrade`** and **`MarketQuote`** — avoid a single ambiguous `Tick` type (**ROADMAP.md** §6 Phase 2C). Derived indicators (footprint, delta, GEX) belong in Market Analysis, not primary storage (**ROADMAP.md** §14).

Test data tiers (small fixtures, integration datasets, full research datasets): **ROADMAP.md** §15.1. Gap tracked as **PRB-017**.

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

### 5.1 Local Data Is Resolved Before Remote Fetching

Historical synchronization should normally prefer already available local data.

The default resolution policy is:

```text
LOCAL_FIRST
```

However, local-first behaviour must be explicit and configurable.

Supported policies should include:

```text
LOCAL_ONLY
LOCAL_FIRST
PROVIDER_REFRESH
PROVIDER_ONLY
```

A workflow must not silently change policy.

---

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

### 5.5 Raw Retention Is Policy-Driven

The framework must not always keep full raw and normalized copies.

Supported policies:

```text
DISCARD_RAW
KEEP_RAW_TEMPORARILY
KEEP_RAW_PERMANENTLY
KEEP_SOURCE_ARCHIVE
```

The policy may depend on:

- provider,
- source format,
- data type,
- cost of reacquisition,
- information loss during normalization,
- audit requirements.

---

### 5.6 Live Storage Must Not Block Live Processing

Live market data is consumed by runtime systems and storage independently.

Correct:

```text
                   ┌── Strategy Runtime
Live Provider ─────┼── Dry Run
                   ├── Monitoring
                   └── Storage Recorder
```

Incorrect:

```text
Live Provider
    ↓
Synchronous Disk Write
    ↓
Strategy Runtime
```

Storage failure must be visible, but storage latency must not become the primary runtime latency path.

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

## 6. Market Data Models

Initial canonical models should include:

```text
Instrument
MarketBar
MarketTrade
MarketQuote
```

Future models may include:

```text
OrderBookUpdate
DOMSnapshot
MarketDepthLevel
OptionsSnapshot
```

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

## 9. Historical Data Synchronization

### 9.1 Purpose

Historical synchronization ensures that a required market data range is available locally.

### 9.2 Workflow

```text
Historical Data Request
        ↓
Resolve Local Dataset Coverage
        ↓
Calculate Missing Ranges
        ↓
Apply Resolution Policy
        ↓
Fetch Missing or Refresh Ranges
        ↓
Normalize
        ↓
Validate
        ↓
Merge and Deduplicate
        ↓
Persist Changed Partitions
        ↓
Register New Dataset Version
        ↓
Return DatasetRef
```

### 9.3 Main Components

```text
HistoricalDataSynchronizer
DatasetRepository
DatasetRegistry
MissingRangeCalculator
HistoricalDataProvider
DataNormalizer
DataValidator
DatasetWriter
```

### 9.4 Important Rules

- Fetch only required ranges unless refresh policy requires otherwise.
- Use Trading Calendar information for expected closures.
- Respect provider request limits and maximum range sizes.
- Do not classify weekends and known holidays as data gaps.
- Do not forward-fill missing market prices by default.
- Persist the resolved synchronization configuration.
- A changed dataset must receive a new version.
- Rewriting one partition must not require rewriting unrelated history.

---

## 10. Missing Range Detection

Missing range detection is a dedicated responsibility.

It must consider:

- requested start and end,
- existing local coverage,
- expected market sessions,
- exchange holidays,
- shortened sessions,
- provider availability,
- contract listing periods,
- contract expiration,
- known outages,
- requested data type and timeframe.

Possible output:

```text
MissingRange(start_at, end_at, reason)
```

A gap is not defined only by timestamp discontinuity.

For futures, the calculator must not request data outside the valid lifecycle of a contract.

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

## 13. Live Data Ingestion

### 13.1 Purpose

Live ingestion receives provider data, normalizes it and distributes it to runtime consumers.

### 13.2 Workflow

```text
Live Provider
    ↓
Provider Adapter
    ↓
Normalization
    ↓
Minimal Live Validation
    ↓
Normalized Market Event Stream
    ├── Market Analysis Runtime
    ├── Strategy Runtime
    ├── Paper Execution
    ├── Monitoring
    └── Live Storage Recorder
```

### 13.3 Rules

- Live data must be normalized before reaching strategy logic.
- Provider SDK objects must not be published internally.
- Runtime delivery and storage recording are separate consumers.
- Slow storage must not block primary market processing.
- Duplicate provider events must be detectable.
- Reconnect and replay behaviour must be explicit.
- Data loss must be observable.
- Backpressure policy must be explicit.

---

## 14. Live Data Recording

Live storage should use batching.

Possible flush policies:

```text
maximum record count
maximum elapsed time
partition boundary
graceful shutdown
memory threshold
```

The recorder must not create one file per event.

Temporary output may contain multiple small files:

```text
working/date=2026-06-18/
├── part-0001.parquet
├── part-0002.parquet
└── part-0003.parquet
```

These files are working ingestion artifacts, not final research datasets.

Live recording should preserve enough provider identifiers to support:

- deduplication,
- ordering,
- gap detection,
- reconciliation after reconnect.

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

## 17. Historical Replay

Historical replay exposes stored data through a stream-like runtime interface.

### 16.1 Workflow

```text
Published Dataset
    ↓
Replay Query
    ↓
Replay Clock
    ↓
Ordered Market Events
    ↓
Runtime Consumers
```

### 16.2 Shared Runtime Contract

Live and replay feeds should expose compatible normalized event contracts where practical.

Possible implementations:

```text
LiveMarketEventStream
ReplayMarketEventStream
RecordedMarketEventStream
```

### 16.3 Important Distinction

Historical replay is not the same as vectorized research.

```text
Vectorized Research / Backtest
```

and:

```text
Event Replay / Runtime Validation
```

are separate execution modes.

The framework should support both without forcing one implementation model onto the other.

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

### 18.2 Storage Layers

Suggested logical layers:

```text
source/
working/
normalized/
derived/
metadata/
```

#### source

Original external archive when retention policy requires it.

It does not need to be query-optimized.

#### working

Temporary ingestion and transformation artifacts.

#### normalized

Canonical provider-specific or source-specific market facts.

#### derived

Datasets constructed from other datasets, including:

- resampled bars,
- continuous futures,
- adjusted series,
- reconstructed bars.

#### metadata

Dataset manifests, checksums, validation results and lineage.

### 18.3 Suggested User Layout

```text
user_data/data/
├── source/
├── working/
├── normalized/
├── derived/
├── cache/
└── metadata/
```

---

## 19. Partitioning Policy

Partitioning is based on data volume, update patterns and query patterns.

Suggested defaults:

| Data Type | Default Partitioning |
|---|---|
| Intraday bars | month |
| Daily bars | year or one file |
| Trades / ticks | day |
| Quotes | day |
| DOM / L2 | day or hour |
| Live working data | batch within day |
| Finalized live bars | month |
| Continuous futures bars | month |

These are defaults, not immutable rules.

### 19.1 Intraday Bars

For data such as NQ 1-minute bars, monthly partitioning is the default.

Example:

```text
bars/1m/year=2026/month=06/data.parquet
```

This supports:

- local updates,
- missing range repair,
- partition replacement,
- efficient query pruning,
- simple finalization.

### 19.2 Avoid Excessive Small Files

Daily partitioning is normally too granular for standard intraday bars.

One file per event or one file per small batch must not become the finalized layout.

Compaction is required when ingestion produces many small files.

### 19.3 Row Groups

Parquet row groups improve query efficiency but do not replace physical partitioning for update and repair workflows.

### 19.4 Quarterly Partitions

Quarterly partitions may be used as a compaction policy for stable historical data, but they must not be confused with futures contract identity.

The default remains monthly for continuous intraday bars because the difference between 28 and 84 files over seven years is operationally negligible, while monthly updates are more flexible.

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

### 20.2 Contract Dataset Layout

Suggested layout:

```text
normalized/
└── databento/
    └── futures/
        └── NQ/
            └── contracts/
                ├── NQH26/
                ├── NQM26/
                ├── NQU26/
                └── NQZ26/
```

For 1-minute bars, one file per contract may be acceptable when the data is imported as a stable historical archive.

For frequently updated contracts, monthly partitions are preferred.

### 20.3 Contract Lifecycle

Contract availability must consider:

- listing date,
- expiration date,
- provider availability,
- first and last trade timestamps,
- exchange calendar,
- roll metadata.

Missing range detection must not request ranges outside the valid lifecycle.

---

## 21. Continuous Futures Data

Continuous futures are derived datasets.

They must never overwrite or replace source contract datasets.

### 21.1 Required Lineage

A continuous futures dataset must record:

```text
source_contracts
roll_policy
roll_dates
roll_trigger
adjustment_method
adjustment_values
construction_version
source_dataset_versions
```

Possible roll policies:

```text
calendar-based
volume-based
open-interest-based
explicit user schedule
```

Possible adjustment methods:

```text
none
backward difference
forward difference
backward ratio
forward ratio
```

### 21.2 Dataset Identity

Different roll or adjustment policies create different datasets.

Example:

```text
NQ continuous 1m / volume roll / backward ratio / v3
```

is distinct from:

```text
NQ continuous 1m / calendar roll / unadjusted / v1
```

### 21.3 Storage

Continuous intraday bars should normally use monthly partitions.

Example:

```text
derived/futures/NQ/continuous/volume_roll_backward_ratio/bars/1m/
└── year=2026/month=06/data.parquet
```

---

## 22. Raw Data Retention

### 22.1 Retention Policies

```text
DISCARD_RAW
KEEP_RAW_TEMPORARILY
KEEP_RAW_PERMANENTLY
KEEP_SOURCE_ARCHIVE
```

### 22.2 Suggested Defaults

#### OHLCV Bars

```text
DISCARD_RAW
```

after successful canonical import, unless the source is costly or unrecoverable.

#### External Vendor Archive

```text
KEEP_SOURCE_ARCHIVE
```

Keep the original compressed file without necessarily creating an additional raw Parquet dataset.

#### Trades and Ticks

```text
KEEP_RAW_PERMANENTLY
```

when bars, footprint or order-flow datasets may be rebuilt later.

#### Quotes, DOM and L2

Usually:

```text
KEEP_RAW_PERMANENTLY
```

or a clearly justified long-term retention policy.

#### Live Data

```text
KEEP_RAW_TEMPORARILY
```

until successful finalization and validation.

### 22.3 Metadata After Raw Deletion

Even when raw data is discarded, retain:

```text
source_id
provider
source_format
source_checksum
imported_at
normalization_version
row_count_before
row_count_after
rejected_rows
validation_report
timezone conversion
symbol mapping
```

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

### 23.2 Live Minimal Validation

Checks only invariants required to protect runtime consumers without creating excessive latency.

Examples:

- timestamp validity,
- instrument identity,
- impossible negative values,
- invalid bid/ask relationship,
- malformed provider event.

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

### 23.4 Failure Policies

Possible outcomes:

```text
FAIL
WARN
QUARANTINE
MARK_INCOMPLETE
ACCEPT_KNOWN_EXCEPTION
```

Invalid records must not be silently dropped without recording the decision.

---

## 24. Public Contracts

Initial contracts should cover the following responsibilities.

### Providers

```text
HistoricalDataProvider
LiveDataProvider
InstrumentProvider
MetadataProvider
```

### Importers

```text
DatasetImporter
ImportInspector
SourceReader
```

### Normalization

```text
DataNormalizer
InstrumentMapper
TimestampNormalizer
```

### Validation

```text
MarketDataValidator
DatasetValidator
ValidationPolicy
```

### Storage and Metadata

```text
MarketDataRepository
DatasetRepository
DatasetRegistry
DatasetWriter
WorkingDataWriter
```

### Services

```text
MissingRangeCalculator
DatasetResolver
HistoricalDataSynchronizer
HistoricalDataQueryService
LiveDataIngestionService
LiveDataRecorder
PartitionFinalizer
DatasetPublisher
HistoricalReplayService
```

Exact method signatures should be defined before concrete adapters are implemented.

---

## 25. Configuration

Market data configuration should support:

- provider,
- importer,
- source path,
- source format,
- instrument mapping,
- data type,
- timeframe,
- date range,
- calendar,
- resolution policy,
- validation policy,
- raw retention policy,
- storage partitioning policy,
- finalization policy,
- roll policy,
- adjustment method.

Configuration must be:

- declarative,
- validated,
- serializable,
- persisted with dataset metadata where material.

Secrets must not be stored in committed configuration.

---

## 26. Suggested Module Structure

```text
src/trading_framework/market/
├── models/
│   ├── instrument.py
│   ├── bar.py
│   ├── trade.py
│   ├── quote.py
│   └── event.py
├── datasets/
│   ├── identity.py
│   ├── metadata.py
│   ├── manifest.py
│   ├── lifecycle.py
│   └── lineage.py
├── requests/
│   ├── historical.py
│   ├── import_request.py
│   ├── query.py
│   └── subscription.py
├── providers/
│   └── protocols.py
├── importers/
│   └── protocols.py
├── repositories/
│   └── protocols.py
├── normalization/
│   └── protocols.py
├── validation/
│   └── protocols.py
└── services/
    ├── missing_ranges.py
    └── dataset_resolution.py
```

```text
src/trading_framework/application/market_data/
├── synchronize_historical.py
├── import_external_dataset.py
├── query_historical.py
├── ingest_live.py
├── record_live.py
├── finalize_partition.py
├── publish_dataset.py
└── replay_dataset.py
```

```text
src/trading_framework/infrastructure/
├── providers/
│   ├── databento/
│   ├── rithmic/
│   ├── binance/
│   └── mt5/
├── importers/
│   ├── databento_dbn/
│   ├── csv/
│   └── parquet/
└── storage/
    ├── parquet/
    ├── duckdb/
    └── metadata/
```

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

---

## 28. Testing Requirements

### Unit Tests

Required for:

- market data model invariants,
- dataset identity,
- dataset lifecycle transitions, including FINALIZED → PUBLISHED,
- missing range calculation,
- partition selection,
- retention policy resolution,
- normalization,
- validation,
- futures contract mapping,
- continuous contract lineage.

### Integration Tests

Required for:

- Parquet repository,
- dataset registry,
- external importer,
- provider adapter,
- live recorder,
- partition finalization,
- dataset publication,
- replay stream.

External provider tests must be opt-in.

### Regression Tests

Required for:

- timestamp corrections,
- schema changes,
- contract roll changes,
- normalization bug fixes,
- gap detection bug fixes.

---

## 29. Initial Implementation Scope

The first Market Data vertical slice should remain limited.

Recommended initial scope:

```text
Instrument
Timeframe
MarketBar
DatasetId
DatasetRef
DatasetMetadata
DatasetLifecycle
DatasetPublication
CSV or Parquet Importer
UTC Normalizer
OHLCV Validator
Parquet Writer
Parquet Repository
Dataset Registry
Historical Query
```

The first complete flow should be:

```text
External File
    ↓
Inspect
    ↓
Normalize
    ↓
Validate
    ↓
Store in Parquet
    ↓
Register Dataset Version
    ↓
Query Through Repository
```

Next increments:

```text
Missing Range Calculator
Historical Provider Synchronization
Live Stream Contract
Live Recorder
Partition Finalization
Dataset Publication
Historical Replay
Futures Contract Datasets
Continuous Futures Builder
```

Databento DBN should be implemented after the generic importer contracts and canonical storage rules are stable.

---

## 30. Final Contract

The Market Data Module must ensure that:

```text
Market facts are provider-independent.

Historical data is resolved locally before remote fetching according to explicit policy.

External file import is separate from provider API synchronization.

Research consumes published dataset versions.

Live market delivery and storage recording are independent consumers.

Working live data is finalized and then explicitly published before becoming a reproducible Research input.

Storage partitioning is based on update and query needs.

Futures contract identity is preserved explicitly.

Continuous futures are derived and fully lineage-aware.

Raw retention is policy-driven rather than automatic.

No single DataManager owns the entire module.
```

All future Market Data implementations must preserve this contract.
