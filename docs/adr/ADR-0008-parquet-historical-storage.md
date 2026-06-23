# ADR-0008 — Parquet Historical Storage

## Status

ACCEPTED

## Context

The Market Data MVP requires durable historical OHLCV storage with stable schema, repository abstraction and local developer workflows without external services.

Architecture documents already identify Apache Parquet as the default analytical storage format, but the sprint needed a concrete MVP implementation decision for bar persistence and path layout.

Sprint 002 implemented:

- canonical `MarketBar` Parquet schema via `pyarrow`,
- `ParquetDatasetRepository` for write and query,
- identity-derived storage paths under a configurable storage root.

## Decision

Use **Apache Parquet** as the MVP historical storage format for canonical OHLCV bars.

Implementation rules:

1. Persist bars through `ParquetBarWriter` using a stable column schema:
   - OHLC as decimal strings,
   - volume as integer,
   - `observed_at` and `available_at` as UTC-normalized timestamps.
2. Access bars through `DatasetRepository`; Research and Strategy must not open Parquet files directly.
3. Derive storage paths from `DatasetRef`, not arbitrary caller-provided paths.

Suggested logical layout under the user storage root:

```text
user_data/data/
├── metadata/
│   └── <instrument>/<data_type>/<timeframe>/<provider>/<source_id>/v<version>.json
└── normalized/
    └── <instrument>/<data_type>/<timeframe>/<provider>/<source_id>/v<version>/bars.parquet
```

The path segments come from `DatasetId` fields and version; identity remains independent from physical location.

## Consequences

### Positive

- columnar storage suitable for analytical workloads,
- repository boundary preserves testability and future storage swaps,
- stable schema supports round-trip tests and integration coverage,
- low operational overhead for local MVP workflows.

### Negative

- adds `pyarrow` as a runtime dependency,
- MVP stores UTC timestamps as naive microseconds in Parquet with UTC semantics applied on read,
- partitioning, compaction and DuckDB adapters remain future work.

## References

- `src/trading_framework/infrastructure/storage/parquet/`
- `src/trading_framework/infrastructure/storage/paths.py`
- `docs/architecture/DATA_MODULE_UPDATED.md` §18
- `docs/architecture/ARCHITECTURE_TECHNICAL_UPDATED.md` §3.8–3.9
