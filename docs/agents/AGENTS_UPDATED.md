# Market Data Module — AI Agent Instructions

## Required Reading

Before modifying the Market Data Module, read:

1. `ARCHITECTURE_FOUNDATIONS.md`
2. `ARCHITECTURE_TECHNICAL.md`
3. `WORKFLOWS_AI_ADR.md`
4. `DATA_MODULE.md`
5. relevant contracts and tests
6. relevant ADRs

Do not implement the task only from the issue description when repository contracts already exist.

---

## Module Ownership

The Market Data Module owns:

- market facts,
- market dataset definitions,
- dataset identity and versioning,
- provider contracts,
- importer contracts,
- normalization contracts,
- validation contracts,
- repository contracts,
- market data access contracts.

It does not own:

- indicators,
- market regimes,
- signals,
- strategies,
- research analytics,
- backtesting,
- broker execution.

---

## Layering Rules

### Domain

Place provider-independent models and contracts in:

```text
src/trading_framework/market/
```

### Application

Place use-case orchestration in:

```text
src/trading_framework/application/market_data/
```

### Infrastructure

Place concrete provider, importer and storage implementations in:

```text
src/trading_framework/infrastructure/
```

Domain and application code must not import provider SDKs or concrete storage adapters.

---

## Mandatory Design Rules

1. Do not create a god-object `DataManager`.
2. Keep historical synchronization, external import, historical query, live ingestion, finalization and replay as separate workflows.
3. Research must not silently download or mutate data.
4. Research should consume explicit published `DatasetRef` versions.
5. Provider schemas and SDK objects must not leak into domain or research logic.
6. Normalize timestamps to timezone-aware UTC at the boundary.
7. Use Trading Calendars for expected market closures and gap detection.
8. Do not forward-fill missing market prices by default.
9. Every persisted dataset requires identity, version, metadata, validation status and lifecycle state.
10. Published dataset versions are immutable.
11. Storage implementations are accessed through repositories.
12. Research and Strategy code must not open Parquet files directly.
13. Live storage must not block live runtime processing.
14. Live events must be written in batches, never one file per event.
15. Working live data must be finalized before publication. Finalization and publication are separate use cases.
16. Raw retention is policy-driven, not automatic.
17. Preserve actual futures contract identity such as `NQM26`.
18. Do not equate calendar quarters with futures contract lifecycle.
19. Continuous futures must be separate derived datasets.
20. Continuous futures must preserve roll and adjustment lineage.
21. Add or update tests for every material change.
22. Update `DATA_MODULE.md` or an ADR when architecture changes.

---

## Data Resolution Policies

Supported historical resolution policies should include:

```text
LOCAL_ONLY
LOCAL_FIRST
PROVIDER_REFRESH
PROVIDER_ONLY
```

Do not hard-code one behaviour into all workflows.

The default for data preparation may be `LOCAL_FIRST`.

The default for a reproducible research run should be effectively `LOCAL_ONLY` against a resolved published dataset.

---

## Dataset Lifecycle

Supported lifecycle states:

```text
WORKING
FINALIZED
PUBLISHED
INVALID
SUPERSEDED
```

Rules:

- `WORKING` may change.
- `FINALIZED` has completed ordering, deduplication, validation and checksumming.
- `PUBLISHED` is stable and can be used by Research or Replay Execution.
- `finalize()` performs `WORKING → FINALIZED`.
- `publish()` performs `FINALIZED → PUBLISHED`.
- A combined helper may call both but must record both transitions.
- `INVALID` must not be used silently.
- `SUPERSEDED` remains available when required for reproducibility.

Never mutate a `PUBLISHED` version in place.

---

## Storage Rules

Use Parquet as the default historical analytical format.

Suggested default partitioning:

| Data Type | Partitioning |
|---|---|
| Intraday bars | month |
| Daily bars | year or one file |
| Trades / ticks | day |
| Quotes | day |
| DOM / L2 | day or hour |
| Live working data | batches within day |
| Continuous futures bars | month |

These are defaults. Changes require a concrete reason based on volume, update pattern or query pattern.

Avoid excessive small files.

Compaction must convert working batches into stable finalized partitions.

---

## Raw Retention Rules

Supported policies:

```text
DISCARD_RAW
KEEP_RAW_TEMPORARILY
KEEP_RAW_PERMANENTLY
KEEP_SOURCE_ARCHIVE
```

Suggested defaults:

```text
OHLCV bars:
    discard raw after validated canonical import

External compressed vendor archive:
    keep source archive when costly or unrecoverable

Trades / ticks:
    usually keep raw

Quotes / DOM / L2:
    usually keep raw or define explicit retention

Live ingestion:
    keep working raw temporarily until finalization
```

Do not create duplicate raw and normalized Parquet datasets without a justified requirement.

---

## Futures Rules

Raw or normalized contract data must preserve:

```text
root symbol
contract symbol
listing or availability range
expiration metadata
source dataset identity
```

Examples:

```text
NQH26
NQM26
NQU26
NQZ26
```

Continuous futures must record:

```text
source contracts
source dataset versions
roll policy
roll dates
roll trigger
adjustment method
adjustment values
construction version
```

Different roll or adjustment policies produce different dataset identities.

Do not overwrite contract datasets with continuous data.

---

## Live Ingestion Rules

Expected flow:

```text
Live Provider
    ↓
Normalize
    ↓
Minimal Validation
    ↓
Normalized Stream
    ├── Market Analysis Runtime
    ├── Strategy Runtime
    ├── Paper Execution
    ├── Monitoring
    └── Storage Recorder
```

Rules:

- storage is a consumer, not a mandatory synchronous gateway,
- duplicate provider events must be detectable,
- reconnect behaviour must be explicit,
- backpressure behaviour must be explicit,
- data loss and recorder failure must be observable,
- provider event identifiers should be preserved when useful for deduplication.

---

## Error Handling

Do not silently:

- drop invalid records,
- fill missing prices,
- ignore duplicated data,
- ignore failed writes,
- ignore incomplete partitions,
- continue after corrupted dataset state,
- replace one provider with another,
- alter roll policy,
- infer instrument mapping from similar symbol names.

Use typed, actionable errors.

Persist validation and rejection summaries where applicable.

Forbidden:

```python
except Exception:
    pass
```

---

## Testing Checklist

Before completing a change, verify:

```text
[ ] Domain ownership is correct
[ ] Provider SDK does not leak outside infrastructure
[ ] Workflow responsibilities remain separated
[ ] Research does not trigger hidden downloads
[ ] UTC and calendar rules are respected
[ ] Dataset identity includes all material inputs
[ ] Finalization and publication are separate
[ ] Published versions remain immutable
[ ] Missing ranges account for expected closures
[ ] Raw retention policy is explicit
[ ] Futures contract identity is preserved
[ ] Continuous futures lineage is complete
[ ] Live storage cannot block the main runtime path
[ ] No excessive small-file pattern was introduced
[ ] Unit tests were added or updated
[ ] Integration tests were added where infrastructure changed
[ ] Documentation or ADR was updated when required
```

---

## Initial Implementation Priority

Prefer small vertical slices.

Recommended order:

```text
1. Market data models
2. Dataset identity and lifecycle
3. Import request and inspection models
4. Normalization and validation contracts
5. Parquet repository contracts
6. CSV or Parquet importer
7. Dataset registry
8. Historical query
9. Missing range calculation
10. Historical synchronization
11. Live stream contract
12. Live recorder
13. Partition finalization
14. Dataset publication
15. Replay
16. Futures contract datasets
17. Continuous futures builder
18. Databento DBN archive import (Phase 2B — after Phase 2A CSV/Parquet OHLCV slice)
```

**Roadmap note:** Data and Research tracks run in parallel (`ROADMAP.md` §3). Phase 2B (archive import) and Phase 6A (OHLCV Strategy Research) are both valid next increments; do not assume a single linear order after Phase 5.

Do not introduce Redis, Kafka, Spark, distributed schedulers or microservices unless a demonstrated requirement justifies them.
