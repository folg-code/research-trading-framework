# ADR-MA-004 — AnalysisDataView and Data Ownership

## Status

ACCEPTED

Amended 2026-08-25 by [ADR-MA-014](ADR-MA-014-marketframe-polars-committed-bulk-engine.md)
for the **bulk** representation contract (D-REP-01). This ADR still owns input immutability,
`DataFieldDependency`, and the live-runtime view.

## Context

Components need efficient OHLCV access without coupling to Parquet, repositories or mutable
DataFrames. Sprint 003 Wave 0 spike compared internal representations before freezing the contract.

## Decision

Engine materializes a read-only `AnalysisDataView` from published market bars:

- columnar `float64` OHLCV fields,
- UTC-ordered timestamps,
- no mutation API on the view.

Components declare `DataFieldDependency` values; they never receive `DatasetRef`, storage paths or
repository handles.

Warm-up range extension happens in the application/executor layer before execution.

Rejected alternative: passing a shared mutable pandas DataFrame as the primary domain model.

## Consequences

### Positive

- input immutability enforced by contract and tests,
- backend-neutral domain layer for **live** and adapter kernels; bulk paths follow ADR-MA-014.

### Negative

- conversion cost at the view boundary (bulk repayment is `MarketFrame`, not more view fields),
- multitimeframe alignment deferred to later phases (landed in ADR-MA-012).

## Amendment 2026-08-25 — bulk contract (D-REP-01)

`AnalysisDataView` remains the executed input type until Stage 4. After ADR-MA-014, it is the
**live-runtime adapter**, not the long-term bulk contract. Components still must not receive
`DatasetRef`, storage paths, or repository handles.

## References

- `docs/vision/MARKET_ANALYSIS_DECISIONS.md` (formerly `MARKET_ANALYSIS_WITH_DECISIONS.md`) — D-011–D-013, D-036
- `docs/planning/sprints/S003_WAVE0_SPIKE_REPORT.md`
- `src/trading_framework/market_analysis/data/view.py`
- `docs/adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md`
