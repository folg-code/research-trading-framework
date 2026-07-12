# ADR-MA-010 — External Analytical Libraries

## Status

ACCEPTED

## Context

NumPy, pandas, TA-Lib and Polars offer performance and indicator coverage. The domain contract must
remain independent from any one library.

## Decision

External libraries are **optional implementation backends**, not part of the public domain contract.

Sprint 003 rules:

1. Default MVP backend: NumPy kernels in `market_analysis/adapters/numpy/`.
2. TA-Lib is an optional extra (S003-T027 deferred); absence must not block the engine.
3. Adapters must pass shared contract tests (D-033): determinism, schema, alignment, warm-up, lineage.
4. Different implementations of the same component need not be bitwise identical but must meet semantic
   contract and documented tolerances (D-034).

Domain protocols (`BatchAnalysisComponent`, `ComponentImplementation`) do not import adapter libraries.

## Consequences

### Positive

- swappable backends without changing planner or registry contracts,
- CI validates NumPy path without TA-Lib installed.

### Negative

- cross-backend numerical parity requires reference datasets and tolerances (TA-Lib task still open).

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-012, D-033, D-034
- `tests/unit/market_analysis/adapters/`
