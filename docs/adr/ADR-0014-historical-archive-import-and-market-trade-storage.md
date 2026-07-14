# ADR-0014 — Historical Archive Import and MarketTrade Partitioned Storage

## Status

ACCEPTED

## Context

Phase 2A (Sprint 002) delivered CSV OHLCV import with single-file `bars.parquet` (ADR-0007, ADR-0008).

Sprint 011 extends the Data Capability Track with **Phase 2B** (archive import foundation) and **Phase 2C.1**
(`MarketTrade` datasets). Available vendor data is Databento DBN **trades**, not OHLCV DBN archives.

Wave 0 spike (`tests/spike/run_databento_dbn_trades_spike.py`) and `S011_WAVE0_DECISIONS.md` validated:

- Databento `trades` schema semantics (`ts_event`, `ts_recv`, side codes),
- day-partition volume on real archives,
- adapter boundary isolation.

## Decision

### First archive slice

Sprint 011 supports **one** Databento schema:

```text
trades  →  canonical MarketTrade
```

Databento DBN OHLCV → `MarketBar` is deferred to increment **2B.2**.

Do **not** introduce a generic `Tick` type.

### Databento dependency boundary

Add `databento` as a **runtime** dependency (`pyproject.toml`, pin `>=0.81.0`).

Rules:

```text
databento imports  →  infrastructure/importers/databento/ only
domain/application →  MarketTrade, protocols, import workflows
```

Enforced by `tests/unit/test_architecture_boundaries.py`.

### MarketTrade model

Canonical fields (MVP):

```text
price, size, event_at, side, received_at?, trade_id?, sequence?
```

`side` normalized to `buy` / `sell` / `unknown`. Databento codes: `B` → buy, `A` → sell, `N` → unknown.

### Trade dataset identity

Extend `Timeframe` with:

```text
tick  — event-level trade datasets (non-bar)
```

Trade imports use:

```text
data_type = trades
timeframe = tick
provider  = databento
```

OHLCV CSV datasets remain unchanged.

### Separate repositories

Do **not** branch bar read/write paths for trade schema:

```text
ParquetDatasetRepository       — OHLCV bars (single bars.parquet)
ParquetTradeDatasetRepository  — trades (day partitions)
```

### Day-partitioned Parquet layout

Partition key = UTC calendar day of `event_at`:

```text
normalized/<instrument>/trades/tick/<provider>/<source_id>/v<version>/
├── partitions/day=YYYY-MM-DD/trades.parquet
└── import_manifest.json
```

Trade Parquet schema: `price` (string), `size` (int64), `event_at`, `side`, nullable
`received_at`, `trade_id`, `sequence`.

### Import manifest and checksum

Every archive import writes `import_manifest.json` with source checksum, symbol mapping,
decode/rejected counts and normalization version.

`DatasetMetadata.checksum` on successful import = **SHA-256 of raw archive bytes** (source checksum).
`finalize_dataset` for trades preserves source checksum; row count is reconciled from stored partitions.

### Dedicated workflows

Do **not** overload CSV OHLCV paths:

```text
import_databento_trades_archive(...)   — new
query_trades(...)                      — new
import_external_dataset / query_historical — unchanged (bars)
```

Reuse: `FileDatasetRegistry`, `finalize_dataset`, `publish_dataset`, lifecycle rules (ADR-0007).

### Symbol mapping (MVP)

Explicit config maps `provider_symbol` → framework `instrument_id`. No symbology resolver or
continuous futures in Sprint 011.

Reader filters rows by `provider_symbol` when the DBN row carries a `symbol` column.

### Test tiers

```text
Tier 1 (CI)   — MockDBNStore + synthetic rows; no local DBN file
Tier 2 (opt-in) — @pytest.mark.tier2_databento; local DBN under user_data/
```

CI integration job excludes `tier2_databento`.

### CLI surface

Thin scripts under `scripts/databento/`:

```text
inspect_dbn.py    — schema-agnostic inspect + checksum
import_trades.py  — import entrypoint
```

### Chunked decode

`DatabentoDBNTradeReader` decodes in bounded chunks. Full resume-after-failure deferred;
failed imports leave no `PUBLISHED` version.

## Consequences

### Positive

- Real trades archives importable through framework contracts,
- archive adapter isolated from domain and application layers,
- day partitions support partition pruning on query,
- CSV OHLCV and bar research paths unchanged,
- CI-safe Tier 1 coverage without proprietary DBN files.

### Negative

- import workflow buffers decoded trades in memory before write (large archives need streaming follow-up),
- single Databento schema only,
- no quote/order-book datasets,
- source checksum on metadata differs from bar content checksum semantics at finalize.

## References

- `docs/planning/sprints/S011_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_011.md`
- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0008-parquet-historical-storage.md`
- `tests/spike/run_databento_dbn_trades_spike.py`
- `tests/integration/market_data/test_databento_trades_import_mocked.py`
