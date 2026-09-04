# Market Data — As-Built Reference

> Extracted from the former `docs/reference/modules/DATA_MODULE.md`'s
> workflow-shaped sections by Sprint 055 T007, per the maintainer-approved
> reversal of Sprint 054 T007's rejection in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1: after Sprint 054's
> `DATA_MODULE_CLASSIFICATION.md` follow-up stripped `DATA_MODULE.md`'s
> future-tier content, what remained was one end-to-end pipeline (acquire →
> import → normalize → validate → finalize → publish → query), not a
> per-package module reference — a workflow narrative filed under the wrong
> tier. `modules/DATA_MODULE.md` is retired; this file replaces it.
>
> Sections already stated elsewhere were dropped in favour of one-line
> pointers rather than duplicated: domain ownership and the dataset-lifecycle
> state list → [`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md)
> (Market Domain); package/test paths and the architectural-layer split →
> [`../system/MODULE_MAP.md`](../system/MODULE_MAP.md) §5; the Parquet
> storage rationale → [`../system/SYSTEM_OVERVIEW.md`](../system/SYSTEM_OVERVIEW.md)
> §3; the `user_data/` workspace tree → `MODULE_MAP.md` §11.
>
> This file also absorbs `SYSTEM_OVERVIEW.md` §3's "Import Paths" table (the
> concrete entry points and their adapter layers), which now points here
> instead of repeating the table.
>
> Residual "suggested/should" target-architecture language survives in some
> sections below (a content defect noted by T001 §6 item 4, not fixed by
> this move).

---

## Purpose

This document defines the market data workflow: how market facts are
acquired, imported, normalized, validated, finalized, published and queried.

The Market Data workflow is shared by:

```text
Signal Research
Strategy Research
Strategy Execution
```

These capabilities may consume the same market data contracts, but they use
different application workflows.

For domain ownership (what the Market Domain owns / does not own) see
[`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md). For packages, dependency
direction and test paths see
[`../system/MODULE_MAP.md`](../system/MODULE_MAP.md) §5 "Market Data
Implementation Map".

---

## Import Paths

> Moved here from `system/SYSTEM_OVERVIEW.md` §3 by Sprint 055 T007 — that
> document now points here instead of repeating the table.

The framework has more than one way to originate a published dataset. Each
import path answers "where does the raw data come from," not "what the data
looks like once published" — every path converges on the same OHLCV or
trades dataset contract (ADR-0007 / ADR-0008), so downstream research never
needs to know which one ran.

| Source | Shape | Entry point | Adapter layer |
|---|---|---|---|
| CSV file | file, provider-neutral | `application/market_data/import_external_dataset.py` | `infrastructure/importers/csv/` |
| Databento DBN archive | file, trades | `application/market_data/import_databento_trades_archive.py` → `derive_ohlcv_from_trades.py` | `infrastructure/importers/databento/` |
| Binance USD-M REST (historical) | network, paginated, OHLCV | `application/market_data/import_binance_futures_ohlcv.py` (CLI: `scripts/market_data/import_binance_ohlcv.py`) | `infrastructure/providers/binance/futures_klines_history.py` |

A reader picks the entry point that matches where the source data lives: a
local vendor file goes through an `infrastructure/importers/` adapter that
reads a file already on disk; a network source goes through an
`infrastructure/providers/` adapter that pages a REST endpoint directly into
`MarketBar` objects — there is no intermediate archive file. Both shapes
converge on the same validate → write bars → register `WORKING` → finalize →
publish sequence; the Binance path additionally applies weight-aware rate
limiting and bounded, jittered backoff before validation, and records any
gap in `import_manifest.json` instead of filling it (ADR-0025).

The Binance **live** adapter (`futures_rest.fetch_closed_klines`,
`futures_websocket.py`) is a separate, unrelated path: it feeds the Sprint
019/020 live dry-run runtime directly, not the dataset registry, and the
historical import path does not modify or wrap it (ADR-0025).

---

## External Dataset Import

### Purpose

External import handles files delivered outside a provider API.

Examples:

- Databento DBN,
- CSV,
- Parquet,
- compressed vendor archives,
- broker exports,
- archived tick files.

### Workflow

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

### Inspect Before Import

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

### API Provider and File Importer Are Different Contracts

Examples:

```text
DatabentoHistoricalProvider
DatabentoDBNImporter
```

They may share normalization code, but they represent different use cases.

---

## Local Historical Data Access

### Purpose

Research and backtesting query published local datasets through repository contracts.

### Workflow

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

Consumers access data through repository contracts, never by opening storage
files directly — see [`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md)'s
Market Domain "Owns" list (repository and access contracts) for the
ownership statement behind this rule.

---

## Partition Finalization

Finalization converts working ingestion data into stable canonical partitions.

### Workflow

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

### Rules

- Finalization must be idempotent where possible.
- Source working files must not be deleted before successful validation and durable final write.
- Failed finalization must leave recoverable state.
- Finalized partitions should normally be immutable.
- A corrected finalized partition creates a new dataset version.

---

## Dataset Publication

Publication exposes a finalized dataset version as a stable input for Research or Replay Execution.

### Workflow

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

## Futures Contract Identity

Raw or normalized futures data must preserve the actual contract identity.

Example:

```text
root_symbol = NQ
contract_symbol = NQM26
expiration_month = 2026-06
```

A contract dataset must not be identified only as `NQ`.

A futures contract is a semantic dataset dimension; a storage partition is a
physical organization mechanism. The framework must not assume `calendar
quarter = futures contract lifecycle`. Continuous futures data is a derived
dataset with explicit roll lineage.

---

## Validation

Validation is separated into stages.

### Import or Batch Validation

Checks:

- schema,
- required fields,
- numeric types,
- timestamps,
- instrument mapping,
- source metadata.

### Final Dataset Validation

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

## Prohibited Designs

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
