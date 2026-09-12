# Sprint 003 — Wave 0 Technical Spike Report

```text
Date: 2026-06-23
Sprint: 003
Wave: 0
Tasks: S003-T002, S003-T003
Dataset: synthetic OHLCV, 98,280 bars (~252 sessions × 390 one-minute bars)
Script: tests/spike/run_market_analysis_backend_benchmark.py
```

## 1. Objective

Validate backend and workspace representation choices before freezing `AnalysisDataView`,
`AnalysisResultStore`, and `AnalysisWorkspace` contracts for Wave 1+.

Questions answered:

1. Is NumPy a viable default adapter backend at realistic bar counts?
2. What is the memory cost of map-of-arrays vs wide DataFrame storage?
3. Is deferred frame assembly cheaper than repeated column concatenation?
4. Does shared dependency reuse avoid redundant work as expected?

---

## 2. Environment

| Item | Value |
|------|-------|
| Python | 3.12 |
| NumPy | 2.5.0 |
| pandas | 3.0.3 |
| TA-Lib | not installed (benchmark skipped) |
| Bar count | 98,280 |

---

## 3. Benchmark Results

| Benchmark | Wall time (s) | Peak memory (MiB) |
|-----------|---------------|-------------------|
| numpy_pipeline (TR, ATR, EMA, rolling max) | 0.203 | 4.50 |
| numpy_map_of_arrays (4 outputs copy) | 0.001 | 3.00 |
| numpy_shared_dependency (TR once → ATR) | 0.005 | 6.00 |
| pandas_pipeline | 0.020 | 13.80 |
| pandas_deferred_frame (OHLCV + outputs) | 0.002 | 6.75 |
| pandas_incremental_concat (4 steps) | 0.002 | 3.01 |
| pandas_wide_concat (single DataFrame) | 0.002 | 6.01 |

Notes:

- NumPy pipeline uses a naive Python-loop EMA; vectorized TA-Lib or `pandas.ewm` is faster for
  EMA alone. Adapter implementations should use vectorized NumPy/pandas/TA-Lib internally.
- pandas pipeline peak memory is ~3× NumPy pipeline for the same operations — supports keeping
  pandas out of the hot execution path.
- Deferred single-shot `DataFrame` assembly and one-shot wide concat are similar in time;
  **incremental concat per component is not required** and deferred assembly is preferred.
- Map-of-arrays storage for four `float64` series uses ~3 MiB peak copy cost — acceptable for
  execution-scoped `AnalysisResultStore`.

---

## 4. Design Decisions (Frozen for Wave 1)

### 4.1 `AnalysisDataView` (canonical market input)

| Decision | Choice |
|----------|--------|
| Public types | No pandas/Polars types in domain contract |
| Column access | Named OHLCV (+ volume) columns as read-only `float64` one-dimensional arrays |
| Time index | Shared UTC bar timestamps aligned with `MarketBar` / `query_historical` ordering |
| Mutability | Read-only; no in-place mutation API |
| Dtype | `float64` for price series (D-027); volume as integer-compatible array |
| Materialization | One view per execution plan; components do not fetch data |

Rationale: spike confirms array-oriented access is memory-efficient; domain stays backend-neutral.

### 4.2 `AnalysisResultStore` (execution-scoped outputs)

| Decision | Choice |
|----------|--------|
| Primary structure | `ComputationIdentity` → `AnalysisResult` → `OutputId` → `float64` array |
| Physical layout | Map-of-arrays (not a single growing DataFrame) |
| Lifetime | Scoped to one execution plan |
| Cache | Exact-match reuse keyed by `ComputationIdentity` within the store |

Rationale: map-of-arrays peak ~3 MiB for four outputs at 98k bars; avoids pandas overhead in
the execution hot path.

### 4.3 `AnalysisWorkspace` (executor-owned)

| Decision | Choice |
|----------|--------|
| Mutation | Only executor registers/removes outputs |
| Component API | Return `AnalysisResult`; never append to shared tables |
| Internal representation | Map-of-arrays + read-only market view reference |
| Wide layout | Not materialized during execution |

Rationale: workspace doc §9 forbidden pattern rejected; spike supports column-oriented storage.

### 4.4 `AnalysisFrame` / assembler (consumer materialization)

| Decision | Choice |
|----------|--------|
| When built | On explicit consumer request after computation |
| MVP assembler backend | pandas `DataFrame` behind `AnalysisFrameAssembler` (application layer) |
| Alias policy | Deterministic aliases; collision = error |
| Domain leakage | `AnalysisFrame` is not a domain aggregate root |

Rationale: deferred assembly ~2 ms vs repeated concat; flat frame only where needed (charting,
research export).

### 4.5 Dependencies

| Package | Sprint 003 role |
|---------|-----------------|
| **NumPy** | Add as **runtime** dependency in Wave 1 — demonstrated need for adapters |
| **pandas** | Remain **dev** until Wave 3 assembler; optional research extra later |
| **TA-Lib** | Optional extra `[talib]`; spike skipped without install; no CI hard dependency |

---

## 5. Shared Dependency Reuse

The spike verifies that ATR from a shared True Range array matches recomputed True Range + ATR.
Planner/executor deduplication by `ComputationIdentity` is validated as semantically sound.

---

## 6. Risks and Mitigations

| Risk | Spike finding | Mitigation |
|------|---------------|------------|
| Hidden copies | Map-of-arrays copy ~3 MiB per 4 outputs | Executor passes views where safe; copy only on cache miss |
| pandas lock-in | Higher memory in pipeline | pandas only in assembler adapter |
| Slow pure-Python loops | NumPy EMA loop slow | Adapters use vectorized libraries internally |
| TA-Lib unavailable | Skipped in CI | NumPy reference adapter required |

---

## 7. Open Items Deferred

- Polars benchmark (optional; not blocking MVP),
- TA-Lib benchmark on CI agent (optional local run),
- Column pruning / release-after-use (architecture hooks only),
- Persistent `DerivedAnalysisDataset`.

---

## 8. Sign-off

Spike results support proceeding to Wave 1 implementation with:

- array-oriented `AnalysisDataView`,
- map-of-arrays `AnalysisResultStore` / `AnalysisWorkspace`,
- deferred pandas-based `AnalysisFrame` assembly,
- NumPy as default runtime numerical backend.

**Status: ACCEPTED** — satisfies S003-T003 and unblocks S003-T004.
