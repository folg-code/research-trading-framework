# ADR-0015 — Derived OHLCV from Published Trades

## Status

ACCEPTED

## Context

Phase 2A (Sprint 002) delivered CSV OHLCV import with single-file `bars.parquet` (ADR-0007, ADR-0008).

Sprint 011 (ADR-0014) delivered Databento **trades** archive import. The project owner's vendor path is
**tick trades only** — OHLCV bars are produced internally by aggregation, not from Databento OHLCV DBN archives.

Sprint 012 was initially scoped as Databento DBN OHLCV direct import (roadmap increment 2B.2). Wave 0 pivot
(2026-07-14) replaced that scope with **derived OHLCV from published trades** (Phase 2B.3). PR #100 (OHLCV DBN
config/inspector) was closed without merge.

Wave 0 spike (`tests/spike/run_trades_to_bars_spike.py`) and `S012_WAVE0_DECISIONS.md` validated:

- UTC left-labeled 1m bucket assignment from `event_at`,
- open/high/low/close/volume aggregation rules,
- bar interval semantics aligned with Phase 2A (`observed_at` = interval start).

## Decision

### Source and target datasets

Input must be a **PUBLISHED** trades `DatasetRef`:

```text
data_type  = trades
timeframe  = tick
```

Output is a new logical dataset:

```text
data_type  = ohlcv
timeframe  = 1m
provider   = derived
source_id  = operator-chosen stable slug
```

First slice supports **`1m` only**. Other bar timeframes are follow-up increments.

### Aggregation semantics

Within each UTC left-labeled 1-minute bucket:

```text
open    = price of first trade  (by event_at, then sequence when present)
high    = max(price)
low     = min(price)
close   = price of last trade   (by event_at, then sequence when present)
volume  = sum(size)
```

Empty buckets produce **no bar** (no zero-volume filler bars in MVP).

Normalization version: `trades-to-bars-v1`.

### Domain boundary

Trades→bars aggregation lives in `market/derivation/`:

```text
DerivedOhlcvFromTradesConfig
TradesToBarsAggregator
```

Do **not** use `market_analysis` OHLCV→OHLCV resample for persisted derived datasets. Market Analysis resample
remains on-the-fly analysis only (ADR-MA-012).

### Persistence layout

Derived OHLCV reuses Phase 2A bar storage:

```text
normalized/<instrument>/ohlcv/1m/derived/<source_id>/v<version>/bars.parquet
```

Single-file `bars.parquet` per dataset version (ADR-0008). No day partitions for derived bars.

### Lineage

Every derived bar dataset version records lineage on `DatasetMetadata.lineage`:

```text
source_dataset_ref     — canonical string of source trades DatasetRef
source_data_type       — trades
derivation_method      — trades_to_bars
derivation_version     — trades-to-bars-v1
target_timeframe       — 1m
```

### Dedicated workflow

```text
derive_ohlcv_from_trades(...)   — new
derive_bars_from_trades.py      — CLI under scripts/market_data/
```

Reads trades via `ParquetTradeDatasetRepository` / `HistoricalTradeQuery`. Does **not** re-decode vendor archives.

Reuse: `OhlcvBarValidator`, `ParquetDatasetRepository`, `finalize_dataset`, `publish_dataset`, `query_historical`,
`FileDatasetRegistry`, lifecycle rules (ADR-0007).

Do **not** overload `import_databento_trades_archive`, CSV `import_external_dataset`, or trade import paths.

### Checksum semantics

`DatasetMetadata.checksum` on import = `"pending"` until `finalize_dataset` computes bar content checksum
(same as CSV OHLCV path). Source trades checksum is preserved on the trades dataset only.

### Test tiers

```text
Tier 1 (CI)   — synthetic MarketTrade rows and mocked DBN trades import; no local DBN required
Tier 2 (opt-in) — derive from locally imported trades under user_data/ when available
```

## Consequences

### Positive

- Operational bar path matches vendor reality (trades → derived 1m OHLCV),
- reuses existing bar persistence and `query_historical` contracts,
- explicit lineage from derived bars to source trades dataset,
- domain aggregation isolated from Databento adapter and Market Analysis resample,
- CI-safe Tier 1 coverage without proprietary archives.

### Negative

- full source trade range loaded into memory before aggregation (large archives need streaming/chunked follow-up),
- `1m` timeframe only in MVP,
- no import manifest on derived datasets (lineage on metadata only; unlike archive imports),
- Databento DBN OHLCV direct import (2B.2) remains deferred.

## References

- `docs/planning/sprints/S012_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_012.md`
- `docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md`
- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0008-parquet-historical-storage.md`
- `tests/spike/run_trades_to_bars_spike.py`
- `tests/integration/market_data/test_derive_ohlcv_from_trades_flow.py`
- `tests/integration/market_data/test_derive_ohlcv_from_trades_mocked.py`
