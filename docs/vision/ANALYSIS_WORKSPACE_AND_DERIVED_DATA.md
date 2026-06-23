# Trading Research Framework

# ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md

## 1. Purpose

This document defines how the framework manages derived analytical data produced from canonical market data.

> **Related:** For engine contracts, component identity, DAG planning, cache scope, and warm-up
> semantics see [`MARKET_ANALYSIS_WITH_DECISIONS.md`](MARKET_ANALYSIS_WITH_DECISIONS.md).
> Where the two documents conflict on workspace or derived-data topics, **this document**
> takes precedence.

It establishes the architecture for:

- wide analytical datasets containing tens or hundreds of columns,
- reusable outputs produced by Market Analysis components,
- temporary helper columns used during computation,
- materialized views consumed by research, backtests, charting, and execution,
- result identity, naming, lineage, deduplication, and lifecycle,
- memory management and future column pruning.

The framework must support complex strategies that depend on many intermediate and final columns without turning a shared DataFrame into the primary domain model.

---

## 2. Context

A complete strategy may require dozens of derived values, for example:

- moving averages and volatility measures,
- session levels and previous-period levels,
- swing and pivot structures,
- distances and normalized distances,
- rolling statistics and percentiles,
- market states,
- signal helper flags,
- exit conditions,
- risk and position-sizing inputs,
- diagnostic columns used during research.

A realistic analytical matrix may therefore contain 30–100 or more columns.

This is expected and supported.

The architectural problem is not the number of columns. The problem is uncontrolled ownership, naming, duplication, mutation, persistence, and reuse.

---

## 3. Core Decision

The framework distinguishes four separate concepts:

```text
MarketDataset
    ↓
AnalysisResultStore
    ↓
AnalysisWorkspace
    ↓
ConsumerView / AnalysisFrame
```

### MarketDataset

Canonical, published market facts owned by the Data Module.

Examples:

```text
timestamp
open
high
low
close
volume
```

### AnalysisResultStore

A logical collection of individually identifiable outputs produced by Market Analysis components.

Examples:

```text
EMA(20)
EMA(50)
ATR(14)
SessionRange
TrendState
VolatilityState
```

### AnalysisWorkspace

A temporary execution environment that combines market data and all outputs required by a particular execution plan.

It may be wide and may contain many derived columns.

### ConsumerView / AnalysisFrame

A materialized view assembled for a specific consumer, such as:

- Market Model Research,
- Signal Research,
- Strategy Backtest,
- Charting,
- Export,
- Execution.

A ConsumerView contains only the outputs required by that consumer.

---

## 4. MarketDataset

`MarketDataset` contains immutable market facts.

It must not be mutated by analytical components.

A MarketDataset:

- is referenced through `DatasetRef`,
- belongs to the Data Module,
- has stable schema and publication identity,
- may be stored in Parquet, Arrow, or another supported format,
- does not contain indicators, states, signals, exits, or risk calculations.

Market Analysis reads from the dataset through a data-access contract.

Components must not:

- open Parquet files directly,
- resolve local paths,
- query providers,
- append columns to the published dataset,
- modify canonical OHLCV values.

---

## 5. AnalysisResult

Each public component execution returns an `AnalysisResult`.

An AnalysisResult represents one resolved computation and contains:

```text
ComputationIdentity
OutputSchema
Outputs
Lineage
Validity metadata
Warm-up metadata
Availability metadata
Diagnostics
```

A component may return one or many public outputs.

Examples:

```text
ATR
└── value

MACD
├── macd
├── signal
└── histogram

LiquiditySweep
├── occurred
├── swept_level
├── depth
└── reclaimed
```

The result must preserve the semantic identity of each output independently of any short DataFrame alias.

---

## 6. Public Outputs and Internal Temporaries

A component may create many local arrays during computation.

Example:

```text
candle_range
body_size
lower_wick
lower_wick_ratio
body_ratio
raw_mask
confirmation_mask
```

These are internal temporaries unless explicitly declared as public outputs.

### Public outputs

Public outputs:

- are declared in `OutputSchema`,
- may be requested by another component,
- may be cached,
- receive stable identity,
- appear in lineage,
- may be materialized in a ConsumerView.

### Internal temporaries

Internal temporaries:

- exist only inside component execution,
- do not enter the global registry,
- do not receive standalone computation identity,
- are not automatically cached,
- are not automatically materialized,
- should be released after component execution.

### Rule

Not every helper column becomes a framework component.

A value should become a public component output only when it has independent analytical meaning or reuse value.

---

## 7. Criteria for Public Component Boundaries

A calculation should normally become a public component or public output when at least one of the following applies:

- it is reused by multiple models or components,
- it has independent analytical meaning,
- it is expensive enough to benefit from shared computation,
- it is useful as a research dimension,
- it requires independent versioning or validation,
- it must be included in lineage,
- it is consumed by another domain such as Signal, Exit, or Risk.

A calculation should normally remain local when it is:

- a simple shift,
- a one-off boolean mask,
- a normalization helper,
- a temporary rolling expression,
- an implementation-specific intermediate array,
- not meaningful outside the parent component.

---

## 8. AnalysisWorkspace

`AnalysisWorkspace` is the execution-time container for all data needed by one resolved plan.

It may contain:

```text
Canonical market-data columns
Shared Market Feature outputs
Market Structure outputs
Market State outputs
Signal Feature outputs
Signal State outputs
Exit helper outputs
Risk helper outputs
Temporary execution metadata
```

The workspace is not the source of truth for component identity.

Identity remains attached to `AnalysisResult` and `OutputRef` objects.

The workspace provides efficient access and temporary materialization.

### Properties

The workspace should be:

- scoped to one execution plan,
- read-only from the perspective of components,
- internally mutable only through the executor,
- column-oriented,
- capable of exposing zero-copy or low-copy views,
- independent from persistent Market Data storage,
- disposable after the workflow completes unless explicitly materialized.

---

## 9. Workspace Ownership

Only the Market Analysis executor may add or remove results from the shared workspace.

Components must return outputs rather than mutate shared state.

Forbidden pattern:

```python
def compute(df):
    df["atr_14"] = ...
    return df
```

Required pattern:

```python
def compute(data, dependencies, parameters, context):
    values = ...
    return AnalysisResult(outputs={"value": values})
```

The executor validates and registers returned outputs.

This prevents:

- hidden columns,
- naming collisions,
- order-dependent behavior,
- accidental overwrite,
- uncontrolled memory growth,
- unsafe parallel execution.

---

## 10. Output Identity and Naming

Every public output has a full semantic identity.

Example:

```text
market.feature.volatility.atr
component_version=1.0.0
implementation=talib.atr
parameters={period: 14}
output=value
```

A full logical output reference may be represented as:

```text
market.feature.volatility.atr[period=14]:value
```

### Aliases

Consumer views may use short aliases:

```text
atr_14
ema_20
trend_state
sellside_sweep
```

Aliases are presentation-level names.

They are not computation identity.

### Alias rules

- aliases must be unique within one ConsumerView,
- collisions must fail explicitly,
- automatic alias generation must be deterministic,
- users may override aliases in model or view definitions,
- aliases must never replace full lineage metadata.

---

## 11. Multi-output Components

The framework must support components returning multiple outputs.

Examples:

```text
BollingerBands
├── lower
├── middle
└── upper

MACD
├── macd
├── signal
└── histogram

SessionRange
├── open
├── high
├── low
├── midpoint
└── completed
```

Dependencies must be able to reference a specific output:

```text
ComponentOutputRef(
    component=SessionRange(...),
    output="low",
)
```

A dependent component must not rely on column-order conventions.

---

## 12. ResultStore

`AnalysisResultStore` maps resolved output identities to results.

Conceptually:

```text
ComputationIdentity
    ↓
AnalysisResult
    ↓
OutputId → array
```

The ResultStore provides:

- lookup by resolved identity,
- output selection,
- dependency injection,
- deduplication,
- execution-cache integration,
- lineage traversal,
- assembly into ConsumerViews.

The ResultStore is not required to use a single physical DataFrame internally.

Possible internal representations include:

- mapping of arrays,
- Arrow table fragments,
- pandas Series objects,
- NumPy arrays,
- backend-native structures.

The contract must not require one representation for every backend.

---

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

## 23. Persistence Decision for Sprint 003

Sprint 003 does not implement persistent storage of derived analytical matrices.

It implements:

- execution-scoped result storage,
- in-memory exact-match cache,
- output identity,
- result assembly contract,
- optional in-memory AnalysisFrame materialization.

Persistent DerivedAnalysisDataset storage is deferred.

---

## 24. Model Definitions and Workspace Requests

Market Models and Signal Models do not directly manipulate workspace columns.

They declare required component outputs.

Example:

```text
MarketModelDefinition
├── EMA(20):value
├── EMA(50):value
├── ATR(14):value
├── TrendState:value
└── VolatilityState:value
```

The planner resolves these requirements into a DAG.

The executor creates the workspace.

The assembler exposes aliases required by the consumer.

Models remain declarative compositions, not active DataFrame-processing classes.

---

## 25. Strategy Composition

A complete strategy may require outputs from multiple domains:

```text
Market Model
× Signal Model
× Exit Model
× Risk Model
```

The execution planner should merge all requirements into one shared plan.

This enables:

- one shared AnalysisWorkspace,
- deduplicated indicators,
- shared structures and states,
- a single aligned backtest view,
- consistent lineage across the strategy.

The strategy definition must not independently calculate or append helper columns.

---

## 26. Debug and Research Outputs

Research workflows may request additional diagnostic outputs that are not required by production execution.

Examples:

```text
raw_signal_mask
rejection_strength
normalized_distance
component_score
condition_a
condition_b
```

These may be declared as optional debug outputs.

A component may define output groups:

```text
core outputs
diagnostic outputs
research-only outputs
```

The planner includes optional outputs only when requested.

This avoids permanently expanding every workspace while preserving research transparency.

---

## 27. Security and Isolation of User Components

User-defined components use the same result contract as framework components.

They must not receive unrestricted ownership of the shared workspace.

User components:

- receive declared inputs,
- return declared outputs,
- cannot overwrite canonical data,
- cannot publish undeclared columns,
- must pass output validation,
- must use explicit aliases when materialized.

This keeps plugin and `user_data` components compatible with framework-level execution guarantees.

---

## 28. Public Contracts

The following should become stable public contracts:

```text
AnalysisResult
OutputSchema
OutputId
OutputRef
AnalysisWorkspaceView
AnalysisFrameRequest
AnalysisFrame
AnalysisFrameAssembler
```

The following should remain internal initially:

```text
workspace physical storage
array ownership implementation
column-pruning algorithm
executor memory policy
cache storage implementation
backend conversion strategy
```

---

## 29. Sprint 003 Requirements

Sprint 003 should include:

- multi-output `AnalysisResult`,
- explicit `OutputSchema`,
- stable `OutputId` and `OutputRef`,
- execution-scoped `AnalysisResultStore`,
- read-only market-data input view,
- executor-controlled result registration,
- deterministic aliases for assembled views,
- collision detection,
- in-memory `AnalysisFrameAssembler`,
- integration test with a wide analytical view,
- no mutation of the source dataset.

The integration test should assemble a frame containing at least:

```text
OHLCV
True Range
ATR
Volatility State
one additional reusable feature
one diagnostic output
```

The objective is to prove that the system supports multiple public outputs and wide workflow views without using a shared mutable DataFrame as its architectural foundation.

---

## 30. Out of Scope for Sprint 003

The following remain outside Sprint 003:

- persistent derived-data cache,
- automatic chunking,
- partial-range cache reuse,
- column pruning implementation,
- distributed result storage,
- parallel DAG execution,
- multitimeframe alignment,
- live incremental workspace,
- full feature-store architecture,
- GPU-specific containers,
- automatic optimizer-driven backend selection.

---

## 31. Testing Requirements

### Contract tests

All components must be tested for:

- declared output presence,
- output length and alignment,
- input immutability,
- deterministic aliases,
- stable output identity,
- multi-output correctness,
- valid warm-up metadata,
- lineage completeness.

### Workspace tests

The workspace must be tested for:

- no source-data mutation,
- no alias collision,
- shared-result reuse,
- correct dependency injection,
- correct final-output selection,
- correct wide-frame assembly.

### Performance tests

The technical spike should measure:

- cost of adding many outputs,
- cost of repeated DataFrame concatenation versus deferred assembly,
- memory usage of map-of-arrays versus wide DataFrame,
- conversion cost for TA-Lib and pandas adapters,
- peak memory for realistic NQ 1-minute datasets.

---

## 32. Architectural Invariants

The following invariants are mandatory:

1. Canonical Market Data is never mutated by Market Analysis.
2. Components return outputs instead of appending columns globally.
3. Every public output has stable semantic identity.
4. Aliases are not computation identity.
5. Internal temporaries are not automatically published.
6. Models declare requirements; they do not own DataFrames.
7. The planner computes only requested outputs and dependencies.
8. Equivalent computations are deduplicated.
9. ConsumerViews are assembled explicitly.
10. Derived analytical matrices are not canonical Market Data.
11. Wide workspaces are supported but remain execution-scoped.
12. Persistent derived data requires explicit materialization and lineage.

---

## 33. ADR Decision

### ADR-MA-007 — Analysis Workspace and Derived Data Materialization

**Status:** Accepted for Sprint 003 planning.

**Decision:**

The framework will use individually identifiable `AnalysisResult` objects as the reusable internal representation of analytical computations. During execution, results are managed within an execution-scoped `AnalysisWorkspace` and `AnalysisResultStore`. Research, backtest, charting, export, and execution workflows may request a flat, wide `AnalysisFrame` assembled from selected market-data and analytical outputs.

The wide frame is a consumer-specific materialization, not the primary domain model and not canonical Market Data.

Components may use internal temporary arrays, but only declared outputs are published to the workspace.

**Consequences:**

Positive:

- supports strategies with dozens of helper columns,
- preserves reuse and deduplication,
- prevents uncontrolled mutation,
- separates semantic identity from column aliases,
- allows backend-specific internal representations,
- supports future memory pruning and persistent derived datasets.

Negative:

- requires explicit result assembly,
- introduces output identity and alias management,
- requires stronger executor and validation contracts,
- is more complex than directly appending columns to a DataFrame.

**Rejected alternative:**

Using one shared mutable DataFrame as the primary execution and domain model.

This alternative was rejected because it creates hidden dependencies, naming collisions, order-dependent execution, weak lineage, repeated calculations, and poor control over memory and persistence.

---

## 34. Summary

The framework accepts that realistic strategies require wide analytical matrices.

The adopted model is:

```text
MarketDataset
= immutable market facts

AnalysisResult
= identifiable reusable computation output

AnalysisWorkspace
= temporary wide execution environment

AnalysisFrame / ConsumerView
= explicit flat materialization for one workflow
```

The architecture does not attempt to eliminate helper columns. It ensures that they are controlled, identifiable, reusable, and materialized only where they are needed.
