# ADR-MA-008 — Cache Identity and Cache Scope

## Status

ACCEPTED

## Context

Identical computations within one plan should not re-execute. Cross-run or partial-range cache reuse
introduces identity and invalidation complexity deferred beyond Sprint 003.

## Decision

Sprint 003 implements an **exact-match, in-memory execution cache** scoped to a single `ExecutionPlan`:

- cache key = `ComputationIdentity.canonical_key()`,
- cache lifetime = one executor run (optional explicit `ExecutionCache` instance),
- planner deduplicates nodes before execution.

Out of scope for MVP:

- persistent cache,
- cross-plan reuse,
- partial-range reuse,
- distributed cache.

Cache identity includes dataset ref, timeframe, parameters, implementation identity and dependency keys.

## Consequences

### Positive

- duplicate `ATR(14)` requests compute once,
- simple, testable semantics.

### Negative

- no cross-run speedup until a future persistent cache ADR.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-018, D-024
- `src/trading_framework/market_analysis/execution/executor.py`
