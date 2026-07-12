# Market Analysis Module (thin guide)

> **Reference doc** — [as-implemented layer](../README.md).  
> Index: [docs/README.md](../../README.md).

**Status:** Sprint 004 complete on `main`; Sprint 005 complete on `sprint/market-analysis-components`.  
Binding decisions (vision): [../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md](../../vision/MARKET_ANALYSIS_WITH_DECISIONS.md), [../../vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md](../../vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md).  
Accepted ADRs: [../adr/README.md](../adr/README.md) (ADR-MA-001–013).

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

Optional session enrichment (Sprint 005): `RunAnalysisRequest.session_resolver` →
`TradingSessionMetadata` on workspace and assembled frame.

Built-in components (`register_mvp_components`):

```text
volatility.true_range → volatility.atr → volatility.state
trend.ema
structure.swing
```

Resampling is **not** a registry component — see ADR-MA-012.

### Session metadata and swing structure (Sprint 005)

```text
run_analysis(session_resolver=CmeEsRthSessionResolver(...))
    → TradingSessionMetadata on AnalysisWorkspace / AnalysisFrame
    → structure.swing on HTF (e.g. 5m) with pivot_range parameter
    → event outputs: EVENT_AT_AVAILABLE on LTF grid
    → state outputs: LAST_CLOSED_BAR on LTF grid
```

See ADR-MA-013 and `S005_SWING_STRUCTURE_CONTRACT.md`.

---

## MVP Components

| ComponentId | Implementation | Notes |
|-------------|----------------|-------|
| `volatility.true_range` | `numpy.true_range` | OHLC data deps |
| `volatility.atr` | `numpy.atr` | depends on TR output |
| `volatility.state` | `numpy.volatility_state` | ATR + threshold; diagnostic `distance_to_threshold` |
| `trend.ema` | `numpy.ema` | close column |
| `structure.swing` | `numpy.swing` | right-window confirmation; event + state outputs; `pivot_range` param |

All components accept optional `computation_timeframe` on `ComponentRequest`.

Swing outputs declare per-field `alignment_policy`: events use `EVENT_AT_AVAILABLE`,
stateful `latest_*` levels use `LAST_CLOSED_BAR` (default).

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
| Alignment | `AlignmentPolicy` (`LAST_CLOSED_BAR`, `EVENT_AT_AVAILABLE`), `AnalysisFrameAssembler` (+ optional `AlignmentCache`) |
| Session | `TradingSessionMetadata` (optional on workspace/frame via `RunAnalysisRequest.session_resolver`) |
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
| MTF swing alignment | `tests/unit/market_analysis/test_mtf_swing_alignment.py` |
| Swing structure | `tests/unit/market_analysis/test_swing_structure.py` |
| Session enrichment | `tests/unit/market_analysis/test_session_metadata_enrichment.py` |
| Single-TF vertical slice | `tests/integration/test_market_analysis_vertical_slice.py` |
| MTF vertical slice | `tests/integration/test_market_analysis_mtf_vertical_slice.py` |
| S005 MTF swing vertical slice | `tests/integration/test_s005_mtf_swing_vertical_slice.py` |
| Visual inspection spike | `tests/spike/run_inspect_mtf_swing.py` (Plotly; optional dev dep) |

---

## Deferred Beyond Sprint 005

| Capability | Notes |
|------------|-------|
| Full Trading Calendar (PRB-007) | CME ES RTH batch MVP in S005; Globex, missing-range, registry deferred — ADR-MA-013 |
| `ResamplingPolicy` / `BoundaryPolicy` enums | deferred until second semantics needed |
| Published HTF dataset vs on-the-fly resample | noted on `ResolvedInputPlan` |
| Optional TA-Lib adapter | S003-T027 / S004-T016 / S005-T017 |
| Additional structure components (BOS, liquidity) | Phase 4+ |
| Persistent derived datasets | ADR-MA-007 consequences |
| Full columnar Polars query path | TD-011, TD-015 |

---

## Design Notes

- **Input contract:** `list[MarketBar]` at the repository boundary; `AnalysisDataView` exposes columnar `float64` for computation.
- **Polars scope:** resample and align only; conversion at boundary to existing view/component path.
- **Partial buckets:** UTC epoch-aligned `group_by_dynamic`; trailing partial bucket emitted when non-empty (ADR-MA-012).
- **Look-ahead:** `LAST_CLOSED_BAR` + backward `join_asof` on `available_at`; event flags use `EVENT_AT_AVAILABLE` (ADR-MA-013); behavior tests in `test_mtf_behavior.py` and `test_mtf_swing_alignment.py`.
- **Cache:** layered in-memory caches scoped to one executor run (`ResampleCache`, `ExecutionCache`, `AlignmentCache`).

---

## Where to Read Next

1. Source: `src/trading_framework/market_analysis/`
2. Session resolver: `src/trading_framework/time/sessions/`
3. ADR: [../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md](../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md), [../adr/ADR-MA-013-cme-es-rth-session-and-swing-structure-mtf-projection.md](../adr/ADR-MA-013-cme-es-rth-session-and-swing-structure-mtf-projection.md)
4. Sprint plans: `docs/planning/sprints/SPRINT_004.md`, `docs/planning/sprints/SPRINT_005.md`
5. Contracts: `docs/planning/sprints/S005_SWING_STRUCTURE_CONTRACT.md`
