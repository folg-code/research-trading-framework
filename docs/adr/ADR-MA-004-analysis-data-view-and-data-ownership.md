# ADR-MA-004 — AnalysisDataView and Data Ownership

## Status

ACCEPTED

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
- backend-neutral domain layer; NumPy kernels stay in adapters.

### Negative

- conversion cost at the view boundary,
- multitimeframe alignment deferred to later phases.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-011–D-013, D-036
- `docs/planning/sprints/S003_WAVE0_SPIKE_REPORT.md`
- `src/trading_framework/market_analysis/data/view.py`
