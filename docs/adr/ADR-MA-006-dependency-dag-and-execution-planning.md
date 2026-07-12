# ADR-MA-006 — Dependency DAG and Execution Planning

## Status

ACCEPTED

## Context

Components may depend on market fields and on outputs of other components. Hidden dependencies would
break cache identity, reuse and testability.

## Decision

`DependencyPlanner` builds a deterministic `ExecutionPlan`:

1. expand explicit `ComponentDependency` and `DataFieldDependency` declarations,
2. resolve parameter-dependent dependencies after canonicalization,
3. deduplicate identical computation nodes,
4. topologically sort nodes,
5. reject cycles with `CyclicDependencyError`.

A DAG node is a **resolved computation** (`ATR(14)` ≠ `ATR(50)`). The engine executes only requested
components and their dependencies (lazy execution).

`SequentialBatchExecutor` is separate from planning; implementations must not call the registry
inside `compute()`.

## Consequences

### Positive

- shared True Range computed once for ATR and downstream state,
- deterministic order and stable plan keys.

### Negative

- no parallel or distributed execution in MVP,
- dynamic dependency graphs beyond parameter-driven refs are unsupported.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-008, D-009, D-016, D-017
- `src/trading_framework/market_analysis/planning/`
