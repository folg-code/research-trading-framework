# ADR-0018 — Continuous Futures Materialization

## Status

ACCEPTED

## Context

Sprint 011 (ADR-0014) imports one Databento `provider_symbol` into one framework `instrument_id`.
Sprint 012 (ADR-0015) derives OHLCV from a published trades dataset. Strategy Research (ADR-0016)
consumes published OHLCV through `query_historical`.

This works for single-contract slices but forces expensive preprocessing on every research run for
multi-year futures backtests:

```text
decode DBN → filter contracts → compute roll → stitch → normalize
```

Architecture foundations state that **continuous futures are derived datasets** and must preserve
contract, roll and adjustment lineage.

Wave 0 decisions (`S015_WAVE0_DECISIONS.md`) and operator requirements define a four-layer pipeline
with versioned materialized output and explicit preprocessing boundaries.

## Decision

### Four-layer pipeline

```text
Raw DBN (immutable, user_data)
    → Normalized Contract Dataset (per actual_contract)
    → Roll Schedule (versioned policy artifact)
    → Materialized Continuous Dataset (partitioned Parquet + manifest)
    → Consumer read (query_trades / query_historical / research workflows)
```

Research consumers read Layer 4 only. They must not build continuous series at run time.

### Contract datasets

Each outright CME contract is a distinct instrument:

```text
NQ.NQM5, NQ.NQU5, …
```

Spread symbols are excluded in MVP.

Contract trades storage:

```text
schema_version     = market-trade-contract-v2
partition key      = session_date (CME RTH, via CmeEsRthSessionResolver)
storage columns    = ts_event_ns, ts_recv_ns, price_nanos, size, instrument_id,
                     sequence, publisher_id, side, product, contract_code,
                     session_date, source_file
```

Domain `MarketTrade` remains unchanged; `ContractTradeRecord` is the contract-layer storage
projection mapped at read/write in infrastructure. Legacy v1 Parquet rows are upgraded on read.

Legacy `import_databento_trades_archive` (single symbol mapping) stays supported.

### Roll schedule

First policy: `volume-rth-close`

```text
evaluate after RTH close
switch at next session open
confirmation_sessions = 1
price_adjustment = none
```

Roll schedule is persisted as a versioned artifact under `continuous/schedules/` and referenced
from continuous dataset lineage. The same schedule drives continuous trades and derived OHLCV.

### Continuous dataset identity

Trades:

```text
NQ.c.0 | trades | tick | continuous | volume-rth-close@N
```

Derived OHLCV (1m):

```text
NQ.c.0 | ohlcv | 1m | derived | volume-rth-close@N
```

Partitioned by `session_date`. No monolithic single-file continuous Parquet. OHLCV 1m uses
`session_date` partitions under `partitions/session_date=*/bars.parquet` with
`continuous_ohlcv_manifest.json` for fingerprint reuse.

Continuous trade rows preserve:

```text
actual_contract, continuous_symbol, roll_id, is_roll_boundary, session_date
```

### Manifest and fingerprint

Each continuous dataset version includes `continuous_manifest.json` with roll policy, builder
versions, roll schedule version and `source_fingerprint`.

Unchanged fingerprint → reuse published dataset. Changed inputs → rebuild affected partitions.

Incremental updates rebuild a configurable trailing window (default **10 sessions**) because new
data may change roll decisions near the series end.

### Price adjustment

Trade and orderflow facts used for simulation and execution research are **not** back-adjusted.
Roll price gaps remain visible; boundaries are flagged with `is_roll_boundary`.

Back-adjusted analytical series are a separate future artifact with distinct `source_id`.

### Preprocessing boundary

New application workflows:

```text
import_databento_contract_trades
build_roll_schedule
materialize_continuous_trades
derive_continuous_ohlcv
build_continuous (orchestration CLI)
```

`run_strategy_research`, `run_signal_research` and dashboard modules must not invoke these
workflows. Missing continuous `DatasetRef` is a hard error with actionable message.

### Lifecycle

Continuous datasets follow ADR-0007:

```text
WORKING → FINALIZED → PUBLISHED
```

Immutability after publish unchanged.

### Implementation (Sprint 015)

Application workflows (orchestrated by `build_continuous`):

| Workflow | Module |
|----------|--------|
| `import_databento_contract_trades_archive` | `application/market_data/import_databento_contract_trades_archive.py` |
| `build_roll_schedule` | `application/market_data/build_roll_schedule.py` |
| `materialize_continuous_trades` | `application/market_data/materialize_continuous_trades.py` |
| `derive_continuous_ohlcv` | `application/market_data/derive_continuous_ohlcv.py` |
| `build_continuous` | `application/market_data/build_continuous.py` |

Domain: `market/contracts/` (identity, `ContractTradeRecord`), `market/continuous/` (roll policy,
schedule builder, materializer config).

Infrastructure highlights:

```text
contract trades     — ParquetContractTradeDatasetRepository (session_date partitions)
roll schedule       — RollScheduleRepository under continuous/schedules/
continuous trades   — ParquetContinuousTradeDatasetRepository + continuous_manifest.json
continuous OHLCV    — ContinuousOhlcvRepository + continuous_ohlcv_manifest.json
roll RTH volumes    — contract_rth_volumes.py (Arrow/Polars per-session, no domain materialization)
```

CLI:

```text
scripts/market_data/build_continuous.py
scripts/market_data/batch_import_contract_trades_range.py
scripts/market_data/run_half_year_backtest.py   (operator validation script)
```

Columnar batch paths (vectorized DBN → Parquet, per-session Polars aggregation) are the
reference implementation for large archives. Full query-path columnar migration (TD-011) remains
deferred for consumer `query_trades` / `query_historical` list contracts.

## Consequences

### Positive

- Long backtests reuse versioned continuous artifacts,
- roll policy and lineage are auditable via manifest,
- contract datasets remain for expiry and roll validation,
- raw DBN can rebuild all layers after policy changes,
- incremental updates avoid full-history recomputation.

### Negative

- additional storage layers and workflows to maintain,
- `session_date` partitions diverge from Sprint 011 UTC `day=` layout,
- MVP limited to NQ trades / volume roll / no back-adjust,
- spread and multi-product orchestration deferred,
- columnar batch reads (TD-011) still future work for consumer query list contracts.

## References

- `docs/planning/sprints/S015_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_015.md`
- `docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md`
- `docs/adr/ADR-0015-derived-ohlcv-from-trades.md`
- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md` (§4.13)
