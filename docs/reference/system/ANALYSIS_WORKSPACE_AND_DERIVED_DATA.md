# Analysis Workspace and Derived Data

This page distinguishes the execution-scoped analytical workspace from persisted user-owned datasets. The detailed [core contract](ANALYSIS_WORKSPACE_CORE.md) and [view/lifecycle contract](ANALYSIS_VIEWS_AND_LIFECYCLE.md) follow the same ownership boundary. Sprint 003 planning and decision text is retained in the [archive](../../archive/audits/ANALYSIS_WORKSPACE_SPRINT_003_DESIGN.md); the [pre-review snapshot](../../archive/snapshots/ANALYSIS_WORKSPACE_AND_DERIVED_DATA_pre_review.md) preserves the full earlier combined page.

## Analytical boundary

A `MarketDataset` supplies trusted market facts. Analytical components produce `AnalysisResult` values with explicit identity, outputs, timeframe and alignment. Public outputs are stable consumable facts; internal temporaries are implementation details. The planner and execution context manage dependencies and reuse rather than requiring consumers to recalculate shared outputs.

## AnalysisWorkspace

An `AnalysisWorkspace` is scoped to a plan or execution. It owns intermediate results and coordinates materialization, cache reuse and memory lifecycle. It is **not** the `user_data/` storage root. See [User Workspace](USER_WORKSPACE.md) for the latter and [Market Analysis Architecture](MARKET_ANALYSIS_ARCHITECTURE.md) for the computation graph.

## Outputs, views and persistence

Component output names and identities must be stable enough for model requests and lineage. Consumer views expose only requested results in a representation appropriate to the consumer; they should not force every computation into one ever-growing wide frame. Column pruning, missing-value semantics and legal availability times remain explicit. Persist derived data only when its reuse and lineage justify a versioned artifact.

## Read next

- [Core contract](ANALYSIS_WORKSPACE_CORE.md): dataset/result identity, public outputs, workspace ownership, cache and result store.
- [Views and lifecycle](ANALYSIS_VIEWS_AND_LIFECYCLE.md): consumer frames, pruning, memory and derived-data persistence.
- [Data Representation Policy](DATA_REPRESENTATION_POLICY.md): accepted target carriers and current implementation status.
- [Time and Alignment](TIME_AND_ALIGNMENT.md): temporal availability and joins.
- [ADR-MA-007](../../adr/ADR-MA-007-analysis-workspace-and-derived-data.md): accepted decision rationale.
