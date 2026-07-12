# ADR-MA-007 — Analysis Workspace and Derived Data Materialization

## Status

ACCEPTED

## Context

Real strategies need wide analytical matrices, but a shared mutable DataFrame as the primary domain
model creates hidden dependencies, weak lineage and uncontrolled memory growth.

Sprint 003 implemented execution-scoped storage and optional `AnalysisFrame` assembly.

## Decision

Use individually identifiable `AnalysisResult` objects as the reusable internal representation.

During one execution:

```text
AnalysisDataView (read-only input)
    → SequentialBatchExecutor
    → AnalysisResultStore (per-output identity)
    → AnalysisWorkspace (executor-owned registration)
    → optional AnalysisFrameAssembler → AnalysisFrame
```

Rules:

1. Only declared outputs enter the store/workspace; temporaries stay inside implementations.
2. `AnalysisFrame` is workflow-specific materialization, **not** canonical Market Data.
3. Presentation aliases ≠ computation identity; alias collisions fail explicitly.
4. Components must not mutate the source market view or append columns to a shared frame.
5. Persistent derived datasets require explicit future materialization with lineage.

Rejected alternative: one shared mutable DataFrame as execution and domain model.

## Consequences

### Positive

- supports wide consumer views without losing reuse metadata,
- separates semantic identity from column aliases,
- enables future memory pruning and derived-dataset persistence.

### Negative

- explicit assembly step for flat consumers,
- stronger executor and validation contracts than ad-hoc DataFrame workflows.

## References

- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` §33
- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — workspace invariants
- `src/trading_framework/market_analysis/storage/`
- `src/trading_framework/market_analysis/assembly/`
