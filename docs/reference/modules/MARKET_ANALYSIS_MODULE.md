# Market Analysis Module (thin guide)

> **Reference doc** — [as-implemented layer](../README.md).  
> Index: [docs/README.md](../../README.md).

**Status:** Sprint 004 complete on `main` — single-TF engine + MTF foundation.  
Binding decisions (vision): [../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md](../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md), [../../vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md](../../vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md).  
Accepted ADRs: [../adr/README.md](../adr/README.md) (ADR-MA-001–012).

---

## Purpose

Deterministic batch analysis over published market datasets:

- register analysis components and implementations,
- resolve dependencies and optional resampling into a DAG,
- execute sequentially with layered deduplication caches,
- store results with identity and lineage in an execution-scoped workspace,
- optionally assemble a wide consumer frame on an evaluation grid.

The domain does **not** use a shared mutable DataFrame as the primary model. Input is
`AnalysisDataView`; outputs are `AnalysisResult` with typed output refs.

---

## Implemented Flow

### Single-timeframe (Sprint 003)

```text
run_analysis()
    load_analysis_data_view()
    RequestResolver.resolve_input_plan()
    DependencyPlanner.build_plan()
    SequentialBatchExecutor.execute()
    optional AnalysisFrameAssembler.assemble()
```

### Multitimeframe (Sprint 004)

When `ComponentRequest.computation_timeframe` is coarser than the dataset timeframe:

```text
source AnalysisDataView (e.g. 1m)
    → ResampleNode (Polars, deduplicated, ResampleCache)
    → resampled AnalysisDataView (e.g. 5m)
    → component execution (unchanged NumPy path)
    → OutputSeries.available_at on HTF outputs
    → AnalysisFrameAssembler aligns to evaluation_timeframe grid (join_asof)
```

`RunAnalysisRequest.evaluation_timeframe` sets the frame index (defaults to source timeframe).

Built-in components (`register_mvp_components`):

```text
volatility.true_range → volatility.atr → volatility.state
trend.ema
```

Resampling is **not** a registry component — see ADR-MA-012.

---

## MVP Components

| ComponentId | Implementation | Notes |
|-------------|----------------|-------|
| `volatility.true_range` | `numpy.true_range` | OHLC data deps |
| `volatility.atr` | `numpy.atr` | depends on TR output |
| `volatility.state` | `numpy.volatility_state` | ATR + threshold; diagnostic `distance_to_threshold` |
| `trend.ema` | `numpy.ema` | close column |

All components accept optional `computation_timeframe` on `ComponentRequest`.

---

## Key Types (entry: `trading_framework.market_analysis`)

| Area | Types |
|------|-------|
| Identity | `ComponentId`, `ComputationIdentity`, `ResampleIdentity`, `AlignmentIdentity` |
| Timeframes | `ComponentRequest.computation_timeframe`; run `evaluation_timeframe` via application |
| Resampling | `ResampleSpec`, `ResampleNode`, `ResampleCache` |
| Resolution | `RequestResolver`, `ResolvedInputPlan`, `ResolvedComponentRequest` |
| Planning | `DependencyPlanner`, `ExecutionPlan`, `PlanningContext` |
| Input | `AnalysisDataView`, `AnalysisContext`, `TimeRange` |
| Output | `AnalysisResult`, `OutputSeries` (`available_at` on HTF), `OutputId`, `Lineage` |
| Alignment | `AlignmentPolicy`, `AnalysisFrameAssembler` (+ optional `AlignmentCache`) |
| Storage | `AnalysisResultStore`, `AnalysisWorkspace` |
| Execution | `SequentialBatchExecutor`, `ExecutionCache` |
| Assembly | `AnalysisFrame`, `AnalysisFrameRequest`, `AnalysisFrameColumnSpec` |

Application: `load_analysis_data_view`, `run_analysis` (`RunAnalysisRequest.evaluation_timeframe`).

---

## Verification

| Area | Location |
|------|----------|
| Adapter contract suite | `tests/unit/market_analysis/adapters/` |
| Execution cache and identity | `tests/unit/market_analysis/test_execution_contracts.py` |
| Workspace and frame assembly | `tests/unit/market_analysis/test_workspace_frame_contracts.py` |
| MTF wave contracts | `tests/unit/market_analysis/test_mtf_wave1_contracts.py` … `test_mtf_wave3.py` |
| MTF behavior regressions (7 areas) | `tests/unit/market_analysis/test_mtf_behavior.py` |
| Single-TF vertical slice | `tests/integration/test_market_analysis_vertical_slice.py` |
| MTF vertical slice | `tests/integration/test_market_analysis_mtf_vertical_slice.py` |

---

## Deferred Beyond Sprint 004

| Capability | Notes |
|------------|-------|
| Exchange/session Trading Calendar (PRB-007) | fixed UTC duration buckets in S004; see ADR-MA-012 |
| `ResamplingPolicy` / `BoundaryPolicy` enums | deferred until second semantics needed |
| Published HTF dataset vs on-the-fly resample | noted on `ResolvedInputPlan` |
| Optional TA-Lib adapter | S003-T027 / S004-T016 |
| Structure components catalog | Phase 4+ |
| Persistent derived datasets | ADR-MA-007 consequences |
| Full columnar Polars query path | TD-011, TD-015 |

---

## Design Notes

- **Input contract:** `list[MarketBar]` at the repository boundary; `AnalysisDataView` exposes columnar `float64` for computation.
- **Polars scope:** resample and align only; conversion at boundary to existing view/component path.
- **Partial buckets:** UTC epoch-aligned `group_by_dynamic`; trailing partial bucket emitted when non-empty (ADR-MA-012).
- **Look-ahead:** `LAST_CLOSED_BAR` + backward `join_asof` on `available_at`; behavior tests in `test_mtf_behavior.py`.
- **Cache:** layered in-memory caches scoped to one executor run (`ResampleCache`, `ExecutionCache`, `AlignmentCache`).

---

## Where to Read Next

1. Source: `src/trading_framework/market_analysis/`
2. ADR: [../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md](../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md)
3. Sprint plan: `docs/planning/sprints/SPRINT_004.md`
4. Spike: `docs/planning/sprints/S004_MTF_SPIKE_AND_DECISIONS.md`
