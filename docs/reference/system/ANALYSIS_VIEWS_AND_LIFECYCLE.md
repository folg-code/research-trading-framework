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

### MVP behavior

For the Market Analysis MVP:

- results may remain materialized for the lifetime of one execution plan,
- the executor uses an in-memory exact-match execution cache,
- ConsumerViews are assembled after required outputs are computed,
- aggressive column pruning is not required.

### Future behavior

The DAG should make future liveness analysis possible.

A result may be released when:

- all dependent nodes have completed,
- it is not requested as a final output,
- it is not required by the selected ConsumerView,
- it is not retained by cache policy.

Example:

```text
TrueRange
    ↓
ATR
    ↓
VolatilityState
```

If `TrueRange` is not a final output and no other node needs it, its data may be released after ATR is computed.

---

---

## 18. Column Pruning

Column pruning is a future optimization, not an MVP requirement.

The architecture must nevertheless preserve:

- dependency-consumer counts,
- final-output declarations,
- view-output declarations,
- cache retention policy,
- clear ownership of arrays.

The executor should eventually distinguish:

```text
required now
required later
required as final output
cache-retained
disposable
```

Pruning must never alter lineage or reproducibility.

---

---

## 19. Physical Representation

The domain contract must not require that the workspace always be a pandas DataFrame.

The physical representation may differ by backend.

Recommended MVP direction:

- NumPy arrays for efficient numerical computation,
- pandas adapters for convenient research and display,
- optional TA-Lib adapters operating on NumPy-compatible arrays,
- future benchmarking of Arrow and Polars.

The framework should minimize:

- full dataset copies,
- repeated Series-to-array conversions,
- repeated dtype conversions,
- repeated index reconstruction,
- automatic DataFrame concatenation after every component.

A flat DataFrame should be created when a consumer actually needs it.

---

---

## 20. Alignment and Index Contract

All outputs in one single-timeframe AnalysisWorkspace must align to a shared time axis.

The executor validates:

- output length,
- output ordering,
- timestamp alignment,
- valid range,
- warm-up region,
- availability metadata.

For the MVP:

```text
source timeframe = computation timeframe = evaluation timeframe
```

Multitimeframe alignment is outside the MVP and must later use explicit resampling and availability-aware alignment nodes.

---

---

## 21. Missing Values and Validity

Derived columns may legitimately contain missing values caused by:

- warm-up,
- insufficient history,
- unavailable session context,
- delayed confirmation,
- sparse event output,
- causal availability constraints.

Missing values must not be silently filled by the workspace.

Each component defines its validity policy.

The result should expose:

```text
valid_from
valid_to
warmup_length
availability semantics
missing-value semantics
```

ConsumerView assembly may apply an explicit policy such as:

- preserve missing values,
- drop rows before all required outputs are valid,
- mask only a selected model output,
- fail when a required output is unavailable.

The policy must be explicit per workflow.

---

---

## 22. Persistence of Derived Data

Derived analytical data is not automatically part of Market Data storage.

### Default

AnalysisWorkspace and ConsumerViews are temporary and in-memory.

### Optional materialization

A workflow may explicitly materialize derived data for:

- long-running research,
- reproducible experiments,
- feature-matrix reuse,
- model training,
- audit and diagnostics,
- large backtest campaigns.

Such data must be stored as a separate artifact class:

```text
DerivedAnalysisDataset
```

It must retain:

- source `DatasetRef`,
- requested outputs,
- computation identities,
- component and implementation versions,
- parameter fingerprints,
- alignment policy,
- assembly policy,
- lineage.

It must not be published as canonical Market Data.

---
