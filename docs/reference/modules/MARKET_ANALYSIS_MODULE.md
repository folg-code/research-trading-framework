# Market Analysis Module (thin guide)

> **Reference doc** — [as-implemented layer](../README.md).  
> Expand after Sprint 003 closure. Index: [docs/README.md](../../README.md).

**Status:** Sprint 003 in progress — Waves 0–4 on `sprint/market-analysis-mvp`.  
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

## Implemented Flow (Wave 4)

```text
run_analysis()                       # application/market_analysis (facade)
    load_analysis_data_view()
    DependencyPlanner.build_plan()
    SequentialBatchExecutor.execute()
    optional AnalysisFrameAssembler.assemble()

Built-in components (register_mvp_components):
    volatility.true_range → volatility.atr → volatility.state
    trend.ema
```

Manual flow remains available via `load_analysis_data_view` + planner + executor.

---

## MVP Components

| ComponentId | Implementation | Notes |
|-------------|----------------|-------|
| `volatility.true_range` | `numpy.true_range` | OHLC data deps |
| `volatility.atr` | `numpy.atr` | depends on TR output |
| `volatility.state` | `numpy.volatility_state` | ATR + threshold; diagnostic `distance_to_threshold` |
| `trend.ema` | `numpy.ema` | close column |

---

## Key Types (entry: `trading_framework.market_analysis`)

| Area | Types |
|------|-------|
| Identity | `ComponentId`, `ComputationIdentity`, `ImplementationId` |
| Planning | `ComponentRequest`, `DependencyPlanner`, `ExecutionPlan` |
| Input | `AnalysisDataView`, `AnalysisContext`, `TimeRange` |
| Output | `AnalysisResult`, `OutputId`, `OutputRef`, `Lineage` |
| Storage | `AnalysisResultStore`, `AnalysisWorkspace` |
| Assembly | `AnalysisFrame`, `AnalysisFrameAssembler`, `AnalysisFrameRequest` |
| Execution | `SequentialBatchExecutor`, `ExecutionCache` |
| Protocols | `BatchAnalysisComponent`, `ComponentImplementation` |

Application: `load_analysis_data_view`, `run_analysis`.

---

## Remaining (Wave 5+)

| Capability | Sprint tasks |
|------------|--------------|
| Adapter contract test suite | T030 |
| Integration test (dedicated) | T031 |
| Workspace/frame regression tests | T041 |
| Market Analysis ADRs | T034–T035 |
| Optional TA-Lib adapter | T027 |

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
