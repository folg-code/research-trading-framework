# Analysis workspace core contract

From the [analysis workspace overview](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md). This page carries the detailed as-built analytical contract.

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
