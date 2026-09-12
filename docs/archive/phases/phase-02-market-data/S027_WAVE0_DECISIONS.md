# Sprint 027 — Wave 0 Decisions

Binding decisions for Market Data Import / Continuous Build Hot-Path Performance.
Date: 2026-07-17.

Inspection basis: phase profiles from NQ half-year batch import and continuous build
(`.tmp_nq_batch_import.log`, `.tmp_nq_half_year_backtest.log`) plus code review of decode,
map, partition write, and continuous materialize paths (2026-07-17).

---

## D-S027-01 — Problem statement

After Sprint 026, research hot paths are operator-viable on NQ half-year scale.

Market Data rebuild remains the dominant wall-clock cost when operators re-import or rebuild
continuous artifacts:

| Stage | Approximate wall (NQ half-year profile) | Dominant phase |
|-------|-------------------------------------------|----------------|
| Batch contract import | ~463 s | `decode_archive` (~202 s self) + `decode.map_chunk_batch` (~61 s) + parquet build/write (~100 s) |
| Continuous build (trades + OHLCV) | ~122 s of build in a ~134 s run | `materialize.write` (~62 s) + transform (~14 s) + derive OHLCV (~22 s) + roll schedule (~16 s) |

Strategy Research on published OHLCV stays ~12–16 s with `--skip-build` and is **out of scope**.

---

## D-S027-02 — Import decode ceiling (vendor)

`decode_archive` self time is almost entirely `databento.DBNStore.to_df(count=chunk_size)` —
waiting for the next pandas chunk between nested map phases. `decode.iter_chunk` is an empty
profile hook and must not be treated as measured decode work.

**Decision:** treat vendor DBN→DataFrame decode as a **measured ceiling**, not a promised
in-sprint win. Wave A starts with a microbench that splits:

```text
to_df / iter_raw_chunks   vs   map_trades_chunk_to_contract_columns   vs   partition write
```

Only pursue decode alternatives (larger `chunk_size`, parallel archives, non-`to_df` APIs) if
the ceiling share leaves enough headroom and the change stays correctness-safe. Do not invent a
custom DBN parser.

---

## D-S027-03 — Import map path root cause (CRITICAL for our code)

`map_trades_chunk_to_contract_columns` normalizes pandas columns to NumPy, then
`ContractChunkColumns.extend_masked` does `array[mask].tolist()` into Python `list` buffers
for every column every chunk. Downstream `take(indices)` and `contract_trade_columns_to_table`
copy those lists again into Arrow.

**Decision:** keep columnar buffers in **NumPy (or Arrow builders)** through decode → session
partition → `pa.Table`. Eliminate `.tolist()` / Python list materialization on the import hot
path. Preserve contract trade Parquet schema and merge-on-session semantics (ADR-0014).

---

## D-S027-04 — Continuous materialize root cause (HIGH)

`materialize_continuous_trades` is sequential per `session_date`: load contract partition →
Polars transform → `pq.write_table`. Profile shows write (~0.18 s/session avg) dominates
transform (~0.04 s). Continuous Parquet still stores `price` as **string** (Decimal-preserving
legacy continuous schema) while contract layer already uses `price_nanos` int64.

**Decision:**

1. First repay **copy / write orchestration** without a schema migration (measure; avoid
   unnecessary casts; keep session partitions).
2. A continuous-schema move to `price_nanos` (align with contract layer) is allowed only with an
   explicit ADR amendment / version bump and a migration or rebuild note — not a silent rewrite.

---

## D-S027-05 — Numeric / columnar stack (import + build)

Same hierarchy as D-S026-07, applied to Market Data ingest:

```text
persist / boundary     → PyArrow / Parquet
tabular transforms     → Polars (continuous map, session dates)
numeric column buffers → NumPy (import chunk map / take)
domain money at edges  → Decimal / price_nanos as today
avoid in hot paths     → list[int] trade buffers, per-row dict records, repeated list→Arrow copies
```

---

## D-S027-06 — Correctness gate

- Contract and continuous Parquet schemas unchanged unless versioned + documented.
- Import validation, session-date partitioning, and merge-existing behaviour preserved.
- Continuous materialize fingerprints / reuse semantics unchanged.
- Fixture + unit equivalence for mapped columns and sample session tables.

---

## D-S027-07 — Priority vs other tracks

Sprint 027 is the **next recommended active Data-track sprint**. Phase 8A polish (S024/S025),
Phase 4B orderflow, and research methodology increments remain queued and must not block Wave A
(import map path).

**Out of scope:** live feeds, quotes import, options, changing roll policy, rewriting OHLCV
bar aggregation algorithms, distributed workers, research methodology changes.

---

## D-S027-08 — Continuous `price` schema (Wave B)

Wave B keeps the continuous Parquet **string `price`** schema (ADR-0018 / current
`MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION`). Non-schema wins ship first:

- cheaper Polars timestamp / price-string formatting,
- skip redundant Arrow casts when schemas already match,
- zstd write without dictionary encoding on high-cardinality prices,
- optional `session_workers` for parallel per-session load/transform/write.

A move to contract-layer `price_nanos` remains deferred to an explicit ADR amendment + version
bump, not a silent rewrite in this sprint.

---

## Key files (pre-sprint)

| Area | Path |
|------|------|
| Batch CLI | `scripts/market_data/batch_import_contract_trades_range.py` |
| DBN reader | `src/trading_framework/infrastructure/importers/databento/reader.py` |
| Contract decode | `src/trading_framework/infrastructure/importers/databento/contract_reader.py` |
| Chunk map | `src/trading_framework/infrastructure/importers/databento/chunk_batch_mapper.py` |
| Column buffers | `src/trading_framework/infrastructure/importers/databento/contract_chunk_columns.py` |
| Contract parquet | `src/trading_framework/infrastructure/storage/parquet/contract_trade_writer.py` |
| Contract repo | `src/trading_framework/infrastructure/storage/parquet/contract_trade_repository.py` |
| Continuous materialize | `src/trading_framework/application/market_data/materialize_continuous_trades.py` |
| Continuous map | `src/trading_framework/infrastructure/storage/parquet/continuous_trade_table_mapper.py` |
| Continuous writer | `src/trading_framework/infrastructure/storage/parquet/continuous_trade_writer.py` |
| ADR | `docs/adr/ADR-0014-*.md`, `docs/adr/ADR-0018-*.md` |
