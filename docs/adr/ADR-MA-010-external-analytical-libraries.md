# ADR-MA-010 — External Analytical Libraries

## Status

ACCEPTED

Amended 2026-08-25 by [ADR-MA-014](ADR-MA-014-marketframe-polars-committed-bulk-engine.md):
Polars is a committed bulk engine. NumPy and TA-Lib remain optional adapter backends.

## Context

NumPy, pandas, TA-Lib and Polars offer performance and indicator coverage. Sprint 003 kept the
domain contract independent from any one library. Sprint 036 D-REP-01 reverses that **only for
Polars on bulk paths**.

## Decision

External libraries except Polars on bulk paths are **optional implementation backends**, not part
of the public domain contract.

Sprint 003 rules:

1. Default MVP backend: NumPy kernels in `market_analysis/adapters/numpy/`.
2. TA-Lib is an optional extra (S003-T027 deferred); absence must not block the engine.
3. Adapters must pass shared contract tests (D-033): determinism, schema, alignment, warm-up, lineage.
4. Different implementations of the same component need not be bitwise identical but must meet semantic
   contract and documented tolerances (D-034).

Domain protocols (`BatchAnalysisComponent`, `ComponentImplementation`) do not import NumPy or
TA-Lib. Bulk contracts may name Polars types (ADR-MA-014).

## Amendment 2026-08-25 — Polars is committed for bulk work (D-REP-01)

Rule 1 still names NumPy as the default **kernel** backend. Polars is no longer “optional
implementation only”: it is the committed engine for bulk frames (`MarketFrame` / `LazyFrame`).
TA-Lib remains optional. Shared contract tests (D-033 / D-034) still bind adapter implementations.

## Consequences

### Positive

- swappable backends without changing planner or registry contracts,
- CI validates NumPy path without TA-Lib installed.

### Negative

- cross-backend numerical parity requires reference datasets and tolerances (TA-Lib task still open).

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-012, D-033, D-034
- `tests/unit/market_analysis/adapters/`
- `docs/adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md`
