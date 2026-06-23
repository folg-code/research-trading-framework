# Market Analysis Module (thin guide)

> **Reference doc** — [as-implemented layer](../README.md).  
> Expand after Sprint 003 closure. Index: [docs/README.md](../../README.md).

**Status:** Sprint 003 in progress — Waves 0–3 merged on `sprint/market-analysis-mvp`.  
Binding decisions (vision): [../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md](../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md), [../../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../../vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md).

---

## Purpose

Deterministic batch analysis over published market datasets:

- register analysis components and implementations,
- resolve dependencies into a DAG,
- execute sequentially with deduplication cache,
- store results with identity and lineage in an execution-scoped workspace.

The domain does **not** use a shared mutable DataFrame as the primary model. Input is `AnalysisDataView`; outputs are `AnalysisResult` with typed output refs.

---

## Implemented Flow (Wave 3)

```text
DatasetRef + TimeRange
    load_analysis_data_view()          # application/market_analysis
        query_historical()             # application/market_data
        AnalysisDataView.from_bars()

ComponentRequest(s)
    ComponentRegistry.resolve()
    DependencyPlanner.plan()           # → ExecutionPlan

SequentialBatchExecutor.execute()
    ComponentImplementation.compute(context, workspace, parameters)
    AnalysisResultStore / AnalysisWorkspace
    ExecutionCache (exact-match, in-plan)
```

Warm-up range extension: `extend_computation_range`, `max_history_requirement` in `execution/warmup.py`.

---

## Key Types (entry: `trading_framework.market_analysis`)

| Area | Types |
|------|-------|
| Identity | `ComponentId`, `ComputationIdentity`, `ImplementationId` |
| Planning | `ComponentRequest`, `DependencyPlanner`, `ExecutionPlan` |
| Input | `AnalysisDataView`, `AnalysisContext`, `TimeRange` |
| Output | `AnalysisResult`, `OutputId`, `OutputRef`, `Lineage` |
| Storage | `AnalysisResultStore`, `AnalysisWorkspace` |
| Execution | `SequentialBatchExecutor`, `ExecutionCache` |
| Protocols | `BatchAnalysisComponent`, `ComponentImplementation` |

Application bridge: `trading_framework.application.market_analysis.load_analysis_data_view`.

---

## Not Yet Implemented (Sprint 003 remainder)

| Capability | Sprint tasks (approx.) |
|------------|------------------------|
| True Range, ATR, EMA, Volatility State components | T025–T028, T040 |
| `AnalysisFrameAssembler`, wide consumer view | T039 |
| `run_analysis` engine facade | T029 |
| Integration test DatasetRef → AnalysisFrame | T031 |
| Market Analysis ADRs | T034–T035 |

---

## Design Notes (MVP)

- **Input contract:** `list[MarketBar]` at the repository boundary; `AnalysisDataView` exposes columnar `float64` for computation.
- **Storage vs analysis:** Parquet keeps prices as string for lossless `Decimal`; the view converts for numerics.
- **Workspace:** executor-owned; components register outputs through the workspace API, not ad-hoc globals.
- **Cache:** in-memory, execution-scoped; identity keyed by `ComputationIdentity`.

---

## Where to Read Next

1. Source: `src/trading_framework/market_analysis/`
2. Tests: `tests/unit/market_analysis/`, `tests/unit/application/market_analysis/`
3. Sprint plan: `docs/planning/sprints/SPRINT_003.md`
4. Spike (data view): `docs/planning/sprints/S003_WAVE0_SPIKE_REPORT.md`
