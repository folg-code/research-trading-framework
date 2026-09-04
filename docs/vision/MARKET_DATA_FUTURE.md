# Trading Research Framework

# MARKET_DATA_FUTURE.md

> **Target architecture / not-yet-built content.** This file (renamed from
> `DATA_MODULE_FUTURE.md` by Sprint 055 T008 — the name now states the
> subject rather than the file it was split from) was originally split out
> of `docs/reference/modules/DATA_MODULE.md` (Sprint-002-era, 674 lines) by
> the follow-up to Sprint 054 T007. It contains every section/subsection of
> that document classified FUTURE, MIXED, or AMBIGUOUS — i.e. content that
> reads as normative/target architecture rather than as-implemented
> behavior, or that could not be confidently verified against the codebase.
> Sprint 055 T008 additionally merged in `docs/vision/ARCHITECTURE_TECHNICAL.md`
> §3.3, §3.5, §3.7, §3.9, §3.10, §3.15 and §3.16 (now dissolved), which
> described the same unbuilt market-data pipeline at a different level of
> verification rigour (see T002 finding F6). See
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` for the full
> section-by-section classification and evidence. Content below is
> preserved verbatim from the original files; only classification headers,
> staleness annotations, and this merge header are newly authored/added.
>
> Former §26 (Suggested Module Structure) and §29 (Initial Implementation
> Scope) were evicted to `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md`
> per Sprint 055 T004 — they describe a layout/increment plan that is
> neither current nor intended, not future architecture.

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

## 3. Provider and Importer Contracts

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §3.3, now dissolved. Classified
AMBIGUOUS by Sprint 054 T002 — as-built status unclear as of Sprint 054, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§3.3. The underlying capability (provider/importer separation) is CURRENT
via `market/importers/` and `infrastructure/providers/`; the specific named
contract protocols below were not found under these names. See §24 below
for the fuller, independently-verified public-contracts picture.)*

Provider contracts may include:

```text
HistoricalDataProvider
LiveDataProvider
InstrumentProvider
MetadataProvider
```

Importer contracts may include:

```text
DatasetImporter
ImportInspector
SourceReader
```

Provider API access and external file import are separate use cases.

They may reuse normalization logic but must not be represented by one ambiguous contract.

---

## 4. Instrument Mapping

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §3.5, now dissolved. Classified
AMBIGUOUS by Sprint 054 T002 — as-built status unclear as of Sprint 054, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§3.5. No dedicated instrument-mapping module or config schema was located.)*

Research instruments and execution instruments may differ.

Examples:

```text
NQ → NAS100
ES → US500
```

Instrument mapping must be explicit.

It must not be inferred from similar symbol strings.

Mappings belong to user-owned configuration or metadata.

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

## 10.1 Missing Data Classification

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §3.7, now dissolved. Classified
AMBIGUOUS by Sprint 054 T002 — as-built status unclear as of Sprint 054, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§3.7. The named policy enum below was not located verbatim; gap-detection
tests exist in spirit.)*

Missing-data handling must distinguish:

```text
Unexpected Gap
```

from:

```text
Expected Market Closure
```

Trading Calendars are required for gap evaluation.

Supported policies may include:

```text
FAIL
WARN
MARK_INCOMPLETE
FETCH_MISSING
ACCEPT_KNOWN_CLOSURE
```

Market prices must not be forward-filled by default.

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

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §3.15, now dissolved.** That
> section (classified FUTURE by Sprint 054 T002 — `execution/modes.py`
> supports only `ExecutionMode.DRY_RUN`; the live-runtime consumer side of
> this pipeline is not built end-to-end) restated this same workflow
> near-identically, adding only: "Storage is an independent consumer" and
> "Slow storage must not block the primary runtime path" — both already
> covered by the Rules above. No unique material to carry forward beyond
> this provenance note.

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

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §3.16, now dissolved.** That
> section (classified FUTURE by Sprint 054 T002 — `execution/modes.py`
> supports only `ExecutionMode.DRY_RUN`; no `ReplayClock` implementation
> exists) restated this same workflow near-identically under the heading
> "Replay", adding a contrast table (batch/vectorized backtest belongs to
> Research; Replay/Paper/Live belong to Execution) — that contrast is
> preserved in full in `EXECUTION_RUNTIME_FUTURE.md`, so it is not
> duplicated here.

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

**Merged from: `ARCHITECTURE_TECHNICAL.md` §3.9, now dissolved.** That
section (classified MIXED by Sprint 054 T002 — the actual, documented
canonical layout is `user_data/market_data/{raw,metadata,normalized,continuous}/`
per `docs/reference/MODULE_MAP.md` §11, a different and narrower set of
directory names than the suggestion above) proposed the same five layers
under a slightly different root (`user_data/data/`) plus one unique layer
not listed above:

#### cache (unique to the merged copy)

Reusable computational artifacts where appropriate.

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

> **Sprint 055 T008 correction (per Sprint 055 T003 G-01):** the
> month-vs-day/session_date partitioning question is not an open divergence
> awaiting a maintainer decision — it is a **settled decision**, recorded in
> two ACCEPTED ADRs: **ADR-0014** (Sprint 011, day-partitioned Parquet layout,
> `partitions/day=YYYY-MM-DD/trades.parquet`) and **ADR-0018** (Sprint 015,
> `partitions/session_date=*/bars.parquet`, which itself already records the
> divergence from Sprint 011's `day=` layout in its own Consequences
> section). `ROADMAP.md` §6 states the resulting rule: day partitioning for
> legacy single-contract import, `session_date` partitioning for
> contract-layer datasets (Sprint 015 onward). Verified in code
> (`infrastructure/storage/paths.py`): **three** coexisting physical
> layouts, none month-based — an unpartitioned `bars.parquet` path (Phase
> 2A/2F Binance imports), `session_date=<date>/bars.parquet` OHLCV
> partitions, `day=<date>` legacy trade partitions, and `session_date=`
> contract/continuous trade partitions. The month-based defaults suggested
> above are this document's forward-looking target-architecture proposal,
> not an unresolved question; see ADR-0008, ADR-0014 and ADR-0018 for the
> as-decided partitioning history.

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §3.10, now dissolved.** That
> section (classified AMBIGUOUS by Sprint 054 T002 — the specific defaults
> table was not verified against actual partition-writer code) carried a
> near-identical version of the table above with an "AMBIGUOUS / not
> verified" caveat instead of the verified divergence finding now
> incorporated above — a concrete instance of Sprint 055 T002 finding F6
> (the same content diverged in confidence level between the two copies).
> No unique material to carry forward beyond this provenance note.

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

> **Sprint 055 T008 correction (per Sprint 055 T003 G-02):** the narrower
> as-built scope above is not an untracked gap — it is a **deliberate MVP
> scope decision** recorded in **ADR-0018** (ACCEPTED, Sprint 015):
> `price_adjustment = none`; "Trade and orderflow facts used for simulation
> and execution research are not back-adjusted"; "Back-adjusted analytical
> series are a separate future artifact with distinct `source_id`";
> Consequences: "MVP limited to NQ trades / volume roll / no back-adjust."
> Back-adjustment specifically is "decided out of v1 scope, with an
> expansion path defined" by ADR-0018; the other roll policies in §21.1
> above (calendar-based, open-interest-based, explicit user schedule) are
> "never evaluated" rather than deliberately deferred. See ADR-0018 for the
> as-decided rationale and the sanctioned expansion path.

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

> **Former §26 (Suggested Module Structure) and §29 (Initial Implementation
> Scope) evicted** to `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` per
> Sprint 055 T004 — see that file for the full content.

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
