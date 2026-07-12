# ADR-MA-011 — Batch Versus Incremental Execution

## Status

ACCEPTED

## Context

Live trading and streaming research eventually need incremental updates. Sprint 003 must deliver a
correct batch foundation without overloading `compute()` with mutable live state.

## Decision

Sprint 003 implements **`BatchAnalysisComponent` only**:

- one plan executes sequentially over a materialized `AnalysisDataView`,
- components are stateless between runs,
- incremental/live execution is a **future executor contract** reusing the same semantic component
  definitions.

Deferred explicitly:

- incremental state storage,
- live bar-by-bar callbacks in domain components,
- distributed or parallel DAG execution.

## Consequences

### Positive

- simpler MVP executor and tests,
- semantic contracts remain valid for a future incremental adapter.

### Negative

- no live update path in Sprint 003,
- incremental design must be revisited before execution-domain integration.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-023
- `src/trading_framework/market_analysis/protocols/batch_component.py`
