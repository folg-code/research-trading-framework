# Trading Research Framework

# DATA_MODULE_FUTURE.md

> **Target architecture / not-yet-built content.** This file was split out
> of `docs/reference/modules/DATA_MODULE.md` (Sprint-002-era, 674 lines) by
> the follow-up to Sprint 054 T007. It contains every section/subsection of
> that document classified FUTURE, MIXED, or AMBIGUOUS — i.e. content that
> reads as normative/target architecture rather than as-implemented
> behavior, or that could not be confidently verified against the codebase.
> See `docs/planning/DATA_MODULE_CLASSIFICATION.md` for the full
> section-by-section classification and evidence. Content below is
> preserved verbatim from the original file; only classification headers
> and staleness annotations (clearly marked as such) were added.

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

> **Verified stale as of this reclassification** (see
> `docs/planning/DATA_MODULE_CLASSIFICATION.md`): live provider streams,
> missing-range resolution, and historical replay have no code counterpart
> anywhere in `src/trading_framework/`. Historical provider APIs (Binance
> only), externally supplied files, local datasets, normalization,
> validation, storage/retrieval, dataset metadata, futures contract
> datasets, and continuous futures datasets are built — see
> `docs/reference/modules/DATA_MODULE.md` and
> `docs/reference/system/MODULE_MAP.md` §5 for what actually exists today.

### Roadmap alignment (2026-07-12)

> **Verified stale as of this reclassification.** This subsection's claim
> that "Phase 2A COMPLETE, everything else PLANNED/GATED" does not match
> the codebase: `MarketTrade` is implemented (`market/models/trade.py`),
> directly contradicting its own "PLANNED (MarketTrade, MarketQuote)" line,
> and a substantial continuous-futures pipeline (contract identity, roll
> policy, materialization, dataset lifecycle integration under
> `market/continuous/` and `market/contracts/`) exists that this subsection
> does not acknowledge at all. `MarketQuote` remains genuinely unbuilt —
> that specific claim is accurate. See
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` for the full analysis. Left
> verbatim below (not edited or deleted) per the reclassification's
> "preserve content, don't rewrite" scope.

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

## 5. Core Principles (not-yet-built)

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

## 6. Market Data Models (not-yet-built / future models)

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

> Note: `Instrument`, `MarketBar` and `MarketTrade` are built (see
> `docs/reference/modules/DATA_MODULE.md` §6); `MarketQuote` and the four
> "future models" above are not.

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

## 18.2 Storage Layers (not-yet-built layout)

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

> Note: the actual layout under `user_data/market_data/` is
> `raw/metadata/normalized/continuous/` — there is no `source/`/`working/`/
> `derived/` tier as described above. See
> `docs/reference/modules/DATA_MODULE.md` §18.3.

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

> **Verified divergence from implementation.** The actual partition key is
> `session_date=<date>` (one partition per exchange session day) for both
> OHLCV bars and trades — no `year=`/`month=` partitioning exists anywhere
> in `src/trading_framework/`. See
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` for details. This is
> flagged as worth a maintainer decision on whether to update this default
> or treat the divergence as a gap.

---

## 20.2 Contract Dataset Layout

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

> Note: `market/continuous/` implements one roll policy
> (`VolumeRthCloseRollPolicy`, volume-based) and no adjustment methods
> today — the lineage concept is real but narrower than described above.
> See `docs/planning/DATA_MODULE_CLASSIFICATION.md` §21.

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

## 23.2 Live Minimal Validation

Checks only invariants required to protect runtime consumers without creating excessive latency.

Examples:

- timestamp validity,
- instrument identity,
- impossible negative values,
- invalid bid/ask relationship,
- malformed provider event.

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

> Note: `DatasetRepository`, `DatasetRegistry` and `DatasetWriter`-equivalent
> contracts exist (`market/repositories/protocols.py`,
> `infrastructure/storage/metadata/registry.py`). Most other named
> contracts above have no code counterpart. See
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` §24.

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

> Note: the real package structure is documented (and kept current) in
> `docs/reference/system/MODULE_MAP.md` §5. This suggested tree is
> partially superseded — e.g. `market/continuous/`, `market/contracts/`,
> `market/derivation/` exist and aren't anticipated here, while
> `infrastructure/storage/duckdb/`, `infrastructure/providers/{rithmic,mt5}/`
> don't exist.

---

## 29. Initial Implementation Scope

> **Partially stale, verified as of this reclassification.** Of the "Next
> increments" listed below, Partition Finalization, Dataset Publication,
> Futures Contract Datasets, and Continuous Futures Builder (narrower than
> described — see §21 above) are already built. Missing Range Calculator,
> Historical Provider Synchronization (in the local-first/policy sense),
> Live Stream Contract, Live Recorder, and Historical Replay remain
> unbuilt. See `docs/planning/DATA_MODULE_CLASSIFICATION.md` §29.

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
