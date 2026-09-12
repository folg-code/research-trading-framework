# Analysis views and lifecycle

From the [analysis workspace overview](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md). This page carries the detailed as-built analytical contract.

## 13. ConsumerView and AnalysisFrame

Research and backtesting often benefit from a flat, aligned analytical matrix.

The framework therefore supports materialization of an `AnalysisFrame`.

Example:

```text
timestamp
open
high
low
close
volume
ema_20
ema_50
atr_14
session_low
sweep_sellside
rejection_strength
trend_state
volatility_state
long_signal
stop_distance
position_size
```

The frame is assembled from selected Market Data and Analysis Results.

```text
MarketDataset
+
Selected AnalysisResults
    ↓
AnalysisFrameAssembler
    ↓
ConsumerView
```

### Important distinction

The AnalysisFrame is:

- a workflow-specific materialization,
- not the primary domain model,
- not automatically persistent,
- not equivalent to MarketDataset,
- not the source of computation identity.

---

---

## 14. Consumer-specific Views

Different workflows may request different views from the same result store.

### Market Model Research View

```text
OHLCV
market features
market structures
market states
market model outputs
forward-return labels
```

### Signal Research View

```text
OHLCV
signal features
signal states
signal model outputs
optional market-model context
forward-return labels
```

### Strategy Backtest View

```text
OHLCV
market model outputs
signal model outputs
exit inputs
risk inputs
position-sizing outputs
```

### Chart View

```text
OHLCV
selected overlays
selected panels
selected event markers
selected states
```

The same underlying result may appear in multiple views without being recomputed.

---

---

## 15. Reuse and Deduplication

The planner resolves all requested outputs into a shared DAG.

When Market Model, Signal Model, Exit Model, and Risk Model request the same computation identity, the executor computes it once.

Example:

```text
Market Model ───────┐
Signal Model ───────┼── ATR(14)
Risk Model ─────────┘
```

Deduplication is based on resolved computation identity, not alias or component name alone.

Different parameterizations remain separate:

```text
ATR(14) != ATR(50)
```

Different implementations remain separate unless explicit equivalence is established:

```text
TA-Lib ATR(14) != NumPy ATR(14)
```

for cache and lineage purposes.

---

---

## 16. Wide Workspaces

The framework explicitly supports wide analytical workspaces.

A wide workspace is not considered an architectural failure.

It is acceptable when:

- every public column has declared origin,
- shared calculations are deduplicated,
- aliases are controlled,
- consumers request explicit outputs,
- internal temporaries remain local,
- unnecessary columns can eventually be released,
- the workspace is not confused with persistent Market Data.

The executor must not compute the entire component catalog.

Only outputs requested directly or through dependencies are included.

---

---

## 17. Memory Lifecycle

The current executor scopes its workspace and exact-match execution cache to
one plan. Required outputs remain materialized for that plan and consumer views
are assembled after computation. There is no general dependency-liveness
release policy. The [future Market Analysis direction](../../vision/MARKET_ANALYSIS_FUTURE.md)
records the proposed release rules.

---

## 18. Column Pruning

General dependency-aware column pruning is not implemented. The current
workspace preserves requested outputs and explicit identity/lineage; see
[Market Analysis Architecture](MARKET_ANALYSIS_ARCHITECTURE.md) for the current
planner. Pruning and retention policy are future extensions.

---

## 19. Physical Representation

The current batch component path uses `AnalysisDataView` with tuple/NumPy
columns. Polars supports resampling and alignment, then converts at the
component boundary; `MarketFrame(pl.LazyFrame, metadata)` is an accepted
**target**, not an implemented carrier. The
[Data Representation Policy](DATA_REPRESENTATION_POLICY.md) separates this
current state from its target.

---

## 20. Alignment and Index Contract

Outputs on one evaluation grid have explicit length, order, availability and
warm-up semantics. Multitimeframe computation is implemented: resampling and
backward as-of alignment use each output's `available_at` and the default
`LAST_CLOSED_BAR` policy. The old single-timeframe-only MVP statement is
historical; see [Time and Alignment](TIME_AND_ALIGNMENT.md) for the actual
contract and its inference-time enforcement limit.

---

## 21. Missing Values and Validity

`AnalysisResult.validity` carries `valid_from_index`, `valid_to_index` and
missing-value semantics; `warmup` and `availability` carry their own metadata.
`OutputSeries` uses `NaN` for missing float values and may expose
`available_at` per value. Sparse event outputs have an explicit inactive fill
under `EVENT_AT_AVAILABLE`. Consumers must preserve the declared validity and
availability meaning rather than silently filling unavailable market facts.

---

## 22. Persistence of Derived Data

The execution-scoped `AnalysisWorkspace` and consumer views are in-memory.
They are not automatically published as Market Data. Predictive and other
research workflows may persist their own versioned feature/result artifacts,
but the proposed generic `DerivedAnalysisDataset` materialization contract is
not implemented. Its lineage and retention requirements remain in
[Market Analysis Future](../../vision/MARKET_ANALYSIS_FUTURE.md).
