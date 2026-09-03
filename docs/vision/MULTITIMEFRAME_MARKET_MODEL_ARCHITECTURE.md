# Trading Research Framework

# Multitimeframe and Market Model Architecture

## 1. Purpose

This document records the architectural decisions concerning:

- multitimeframe analysis,
- Market Analysis responsibilities,
- Market Analysis components,
- Market Model composition,
- temporal alignment,
- research-space growth,
- storage and analysis of large result spaces.

The purpose of this document is to prevent the framework from evolving toward:

- hidden timeframe dependencies,
- duplicated feature computation,
- monolithic Market Models,
- uncontrolled Cartesian-product research,
- manual inspection of millions of results,
- look-ahead bias caused by incorrect higher-timeframe alignment.

This document complements:

- `ARCHITECTURE_FOUNDATIONS.md`,
- `ARCHITECTURE_TECHNICAL.md`,
- `WORKFLOWS_AI_ADR.md`.

---

# 2. Core Decision

A Market Model is not an analytical feature.

A Market Model is a named, versioned and declarative composition of analytical outputs produced by the Market Analysis domain.

The architecture is:

```text
Market Data
    ↓
Market Analysis Components
    ├── Features
    ├── Structures
    └── States
            ↓
    ┌───────┴────────┐
    ↓                ↓
Market Model     Signal Model
```

The Market Analysis domain calculates reusable descriptions of the market.

The Market Model selects and combines those descriptions into a specific market-context hypothesis.

---

# 3. Market Analysis Responsibilities

## 3.1 Market Analysis Question

Market Analysis answers:

```text
What analytical information can be derived from market data?
```

It owns reusable calculations and classifications that can be consumed independently by:

- Market Models,
- Signal Models,
- Signal Research,
- Strategy Research,
- live execution.

Market Analysis does not decide whether a trade should be entered, exited or sized.

---

## 3.2 Market Analysis Categories

The Market Analysis domain exposes three semantic output categories:

```text
Market Analysis Components
├── Features
├── Structures
└── States
```

All categories may use the same Market Analysis Engine, dependency graph, cache and execution contracts.

The categories express meaning and result shape. They do not require separate computation engines.

---

## 3.3 Features

Features produce scalar, categorical, vector or time-series outputs.

Examples:

- ATR,
- rolling volatility,
- RSI,
- VWAP,
- slope,
- momentum,
- volume delta,
- distance to session high,
- distance to VWAP.

A Feature may be an input to another Feature, Structure or State component.

---

## 3.4 Structures

Structures represent richer market objects or detected events.

Examples:

- swing structure,
- session range,
- fair value gap,
- liquidity sweep,
- order block,
- liquidity pool,
- higher high,
- lower low.

Structures should use typed schemas or structured datasets.

They should not default to untyped dictionaries.

---

## 3.5 States

States classify reusable market conditions from Features, Structures and Market Data.

Examples:

```text
trend = bullish
volatility = high
momentum = weakening
structure = ranging
liquidity = compressed
market_phase = expansion
```

Possible State families:

```text
States
├── Trend States
├── Volatility Regimes
├── Momentum States
├── Liquidity States
├── Structural States
└── Market Phases
```

Examples:

- `TrendState`,
- `VolatilityRegime`,
- `MomentumState`,
- `LiquidityState`,
- `StructuralState`,
- `MarketPhase`.

A State component remains reusable and strategy-independent.

It may depend on:

- Features,
- Structures,
- raw or normalized Market Data,
- time abstractions,
- sessions,
- calendars.

---

# 4. Boundary Between Market Analysis and Strategy

The boundary is:

```text
Market Analysis:
What reusable analytical information can be derived?

Market Model:
Which analytical conditions define the market context?

Signal Model:
Which analytical events and conditions define a trading opportunity?

Strategy Model:
How are Market, Signal, Exit and Risk Models composed?
```

Examples that belong to Market Analysis:

```text
trend = bullish
volatility = normal
market structure = continuation
price is above VWAP
liquidity state = compressed
```

Examples that do not belong to Market Analysis:

```text
good environment for London Sweep
avoid long entries
breakout entry allowed
preferred strategy context
```

These are strategy-specific interpretations and should be expressed through Market Model composition or higher-level strategy definitions.

---

# 5. Market Model Definition

## 5.1 Market Model Question

A Market Model answers:

```text
Which combination of analytical market conditions defines the context under study?
```

It does not calculate ATR, trend, volatility regime or market structure internally.

It consumes their previously calculated outputs.

---

## 5.2 Market Model as Expression Tree

A Market Model is an explicit logical expression over Market Analysis outputs.

A Signal Model follows the same technical pattern. The distinction is semantic, not computational.

Example:

```text
Bullish Expansion Model
=
Trend State 4h == bullish
AND
Volatility Regime 1h == expanding
AND
Structural State 30m == bullish continuation
AND
Price Above VWAP 1m == true
```

Conceptual definition:

```python
@dataclass(frozen=True, slots=True)
class MarketModelDefinition:
    id: str
    version: int
    expression: MarketExpression
```

A leaf condition may reference a Market Analysis request:

```python
@dataclass(frozen=True, slots=True)
class ComponentCondition:
    component_request: ComponentRequest
    operator: ComparisonOperator
    expected_value: object
```

---

## 5.3 Market Model Ownership

The Market Model Definition remains in the Strategy domain because it expresses a strategy-relevant market context.

The analytical algorithms used by the Market Model remain in Market Analysis.

Therefore:

```text
Market Analysis owns Features, Structures and States.
Strategy owns Market Model and Signal Model composition.
```

This prevents Market Analysis from becoming coupled to specific trading ideas.

---

## 5.4 Market and Signal Models Must Remain Lightweight

A Market Model or Signal Model Model must not:

- fetch data,
- resample data,
- calculate indicators,
- calculate Structures,
- calculate Market Analysis states,
- access provider SDKs,
- open Parquet files,
- implement Signal logic,
- implement Exit logic,
- implement Risk logic.

It should only:

- identify required analytical outputs,
- define logical conditions,
- preserve component lineage,
- evaluate a logical expression over aligned results.

---

# 6. Multitimeframe Architecture

## 6.1 Core Principle

Multitimeframe is not a special strategy type and not a special Market Model type.

It is a natural property of analytical component requests.

Each Market Analysis component may be instantiated on a selected timeframe.

Example:

```text
Trend State 4h
Volatility Regime 1h
Structural State 30m
Price Above VWAP 1m
```

Market and Signal Models may compose these outputs without requiring separate multitimeframe logic.

---

## 6.2 Timeframe Is Part of Component Identity

A single implementation should support multiple timeframe-specific instances.

Correct:

```text
ATR(period=14, timeframe=30m)
ATR(period=14, timeframe=1h)
ATR(period=14, timeframe=4h)
```

Incorrect:

```text
ATR30m
ATR1h
ATR4h
```

The full identity of a calculated analytical node should include all material temporal inputs.

Suggested dimensions:

```text
component_id
component_version
parameters
instrument
source_dataset
source_timeframe
computation_timeframe
evaluation_timeframe
resampling_policy
alignment_policy
calendar_version
```

---

## 6.3 Source, Computation and Evaluation Timeframe

The framework must distinguish three concepts.

### Source Timeframe

The granularity of the source dataset.

Example:

```text
NQ 1m bars
```

### Computation Timeframe

The granularity on which an analytical component is calculated.

Examples:

```text
Volatility Regime on 30m
Trend State on 1h
Market Phase on 4h
```

### Evaluation Timeframe

The granularity on which the Market Model or Signal Model is evaluated.

Example:

```text
Signal evaluated every 1m
```

Example configuration:

```text
source timeframe:       1m
signal evaluation:      1m
volatility computation: 30m
trend computation:      1h
market phase:            4h
```

These concepts must not be conflated.

---

# 7. Resampling

## 7.1 Resampling Is a Shared Dependency

Resampling must be represented as an explicit node in the dependency graph.

Example:

```text
NQ 1m Bars
   ├── Resample to 30m
   │      └── Volatility Regime 30m
   ├── Resample to 1h
   │      └── Trend State 1h
   └── Resample to 4h
          └── Market Phase 4h
```

The same resampled dataset should be reused by all components requiring it.

A component must not privately resample source data inside its own calculation method.

---

## 7.2 Derived Datasets

Resampled datasets belong to the derived data layer.

Suggested location:

```text
user_data/data/derived/
```

A derived dataset should preserve:

- source dataset identity,
- source timeframe,
- target timeframe,
- resampling rules,
- calendar version,
- boundary convention,
- dataset version,
- checksum where applicable.

---

## 7.3 Resampling Contract

Conceptual model:

```python
@dataclass(frozen=True, slots=True)
class ResampleRequest:
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    calendar_id: str
    boundary_policy: BoundaryPolicy
```

The resampling implementation should be reusable by:

- Market Analysis Engine,
- dataset generation workflows,
- research workflows,
- replay and execution preparation.

---

# 8. Temporal Alignment and Look-Ahead Protection

## 8.1 Main Risk

The main multitimeframe risk is not resampling itself.

It is making higher-timeframe information available before that information was known.

Example:

```text
Decision time: 10:37
Higher timeframe: 1h
Current 1h interval: 10:00–11:00
```

At 10:37, the final high, low, close, volume, ATR and regime of the 10:00–11:00 bar are not available.

The framework must not expose their final values to a 1m decision at 10:37.

---

## 8.2 Default Alignment Policy

The default policy is:

```text
LAST_CLOSED_BAR
```

A higher-timeframe result becomes available only after the underlying higher-timeframe interval is closed and the result is calculated.

Example:

```text
4h interval:   08:00–12:00
available_at:  12:00
```

The value may then be used by lower-timeframe observations occurring at or after `available_at`.

---

## 8.3 As-Of Alignment

Higher-timeframe outputs should normally be aligned to lower-timeframe observations using backward as-of semantics.

Conceptually:

```text
For each lower-timeframe timestamp,
use the most recent higher-timeframe result
whose available_at <= evaluation timestamp.
```

A normal equality join is insufficient.

A blind forward-fill is unsafe unless it is based on explicit `available_at` semantics.

---

## 8.4 Observed Time and Available Time

Analytical results should preserve two temporal concepts:

```text
observed_at
available_at
```

`observed_at` describes the source market interval.

`available_at` describes when the result may legally be consumed.

Conceptual model:

```python
@dataclass(frozen=True, slots=True)
class TemporalAnalysisResult:
    component_key: ComponentKey
    timeframe: Timeframe
    observed_at: TimestampRange
    available_at: datetime
    payload: AnalysisPayload
```

This distinction supports:

- automatic look-ahead validation,
- replay consistency,
- research/execution parity,
- correct multitimeframe joins.

---

## 8.5 Intrabar Exception

Incomplete higher-timeframe data may be used only when the model explicitly studies intrabar state.

Such a component must declare:

- that it consumes partial intervals,
- how partial bars are constructed,
- its update frequency,
- its `available_at` policy,
- whether research and live execution use identical semantics.

Intrabar behaviour must never be the accidental result of ordinary resampling.

---

# 9. Component Request

A timeframe-aware analytical component request may be represented as:

```python
@dataclass(frozen=True, slots=True)
class ComponentRequest:
    component_key: ComponentKey
    parameters: ParameterSet
    source_timeframe: Timeframe
    computation_timeframe: Timeframe
    evaluation_timeframe: Timeframe
    resampling_policy: ResamplingPolicy
    alignment_policy: AlignmentPolicy
```

A decorator may exist as optional syntax sugar, but it must produce or register an explicit `ComponentRequest`.

A decorator must not hide:

- timeframe dependencies,
- resampling rules,
- alignment rules,
- warm-up requirements,
- cache identity,
- data lineage.

The framework contract must remain explicit and serializable.

---

# 10. MarketFieldReference

Model expressions must not access arbitrary DataFrames, Parquet files or storage objects.

Simple source-data conditions may use a controlled:

```text
MarketFieldReference
```

A reference must preserve:

```text
dataset lineage
field identity
source timeframe
evaluation timeframe
available_at semantics
```

It participates in dependency resolution and temporal validation.

---

# 11. Market and Signal Model Examples


```yaml
market_model:
  id: bullish_expansion
  version: 1

  expression:
    operator: AND
    children:
      - component: trend_state
        timeframe: 4h
        condition:
          equals: bullish

      - component: volatility_regime
        timeframe: 1h
        condition:
          equals: expanding

      - component: structural_state
        timeframe: 30m
        condition:
          equals: bullish_continuation

      - component: price_above_vwap
        timeframe: 1m
        condition:
          equals: true
```

The Market Analysis Engine resolves and calculates the Market Analysis dependencies.

The Market Model evaluator only applies the expression to aligned outputs.


Signal Model example:

```yaml
signal_model:
  id: bullish_sweep
  version: 1

  expression:
    operator: AND
    children:
      - component: liquidity_sweep
        computation_timeframe: 1m
        condition:
          field: direction
          equals: bullish

      - component: price_reclaim
        computation_timeframe: 1m
        condition:
          equals: true
```

The Market Analysis Engine resolves shared dependencies for both model types.
The model evaluator applies the expression only to resolved and legally available outputs.

---


# 12. Research-Space Growth

## 11.1 The Problem

Multitimeframe analysis expands the number of possible component combinations.

Example dimensions:

```text
4 analytical properties
4 timeframe alternatives
5 parameter variants
```

Naive combination growth may become extremely large before adding:

- Signals,
- Exits,
- Risk Models,
- instruments,
- periods,
- execution assumptions.

A fast engine does not solve the statistical problem.

It may only produce overfitted results faster.

---

## 11.2 No Implicit Full Cartesian Product

The framework must not interpret every list of timeframe or parameter values as a mandatory full Cartesian product.

Configuration must distinguish:

```text
fixed selection
independent alternatives
bounded search space
logical composition
```

These have different meanings.

---

## 11.3 Fixed Selection

One explicit model:

```yaml
trend_state:
  timeframe: 4h

volatility_regime:
  timeframe: 1h
```

This creates one Market Model definition.

---

## 11.4 Independent Alternatives

A focused comparison:

```yaml
trend_state:
  timeframe:
    experiments:
      - 30m
      - 1h
      - 4h
```

This creates three comparable variants.

It does not imply that all other dimensions must expand simultaneously.

---

## 11.5 Search Constraints

A bounded research space may declare constraints such as:

```yaml
constraints:
  max_components: 4
  max_distinct_timeframes: 3
  require_context_timeframe_gte_signal_timeframe: true
  forbid_duplicate_analysis_category: true
```

Possible semantic constraints:

```text
trend timeframe >= signal timeframe
context timeframe >= entry timeframe
maximum number of Market Model conditions
maximum number of independent parameters
maximum model complexity
```

The planner should reject or prune invalid combinations before computation.

---

# 13. Hierarchical Research Methodology

The framework should encourage progressive research rather than immediate full-grid Strategy Research.

## Stage 1: Individual Components

Test one market property at a time.

Examples:

```text
Trend State 1h as a one-condition Market Model
Trend State 4h as a one-condition Market Model
Liquidity Sweep as a one-condition Signal Model
Signal Model × Trend Market Model
```

Questions:

- Does the property add information?
- Which timeframe is meaningful?
- Is the sample size sufficient?
- Is the effect stable over time?
- Does it generalize across instruments?

---

## Stage 2: Pairwise Interactions

Test only promising pairs.

Examples:

```text
Trend State 4h × Volatility Regime 1h
Trend State 1h × Structural State 30m
Market Phase 4h × Volatility Regime 30m
```

---

## Stage 3: Small Model Compositions

Build compact Market Models and Signal Models from validated components.

Preferred initial size:

```text
2–4 analytical conditions
```

A larger model requires stronger evidence and explicit complexity justification.

---

## Stage 4: Complete Strategy Research

Only selected Market Models and Signal Models are combined with:

```text
Exit Model
Risk Model
```

This produces complete Strategy Model candidates.

---

## Stage 5: Validation

Selected candidates should undergo:

- out-of-sample validation,
- walk-forward analysis,
- parameter perturbation,
- cost sensitivity,
- cross-asset analysis,
- Monte Carlo analysis,
- family analysis.

---

# 14. Research Result Architecture

## 13.1 Do Not Create One Giant Experiment Matrix

The framework should not create a separate wide DataFrame column for every complete experiment combination.

Avoid:

```text
rows = every market timestamp
columns = every Market Model × Signal Model × timeframe combination
```

This creates poor memory characteristics and difficult lineage.

---

## 13.2 Separate Data Layers

Recommended layers:

```text
Derived Market Datasets
        ↓
Market Analysis Cache
        ↓
Market Analysis Results
        ↓
Market Model Results / SignalOccurrences
        ↓
Signal Research Dataset
        ↓
Strategy Research Dataset
        ↓
Analytics and Reports
```

Each layer has a separate identity and persistence policy.

---

## 13.3 Market Analysis Cache

Feature outputs may use a wide, computation-friendly representation.

Example:

```text
timestamp
atr_14__30m
atr_14__1h
trend_state__1h
trend_state__4h
```

These are reusable analytical outputs, not complete experiment results.

---

## 13.4 Market Model Results

Boolean Market Model states may be represented as:

- boolean masks,
- bitsets,
- categorical arrays,
- integer state codes,
- sparse event tables where appropriate.

An experiment should reference reusable state identities rather than copy the entire time series.

---

## 13.5 Research Results

Research results should use queryable fact tables and explicit lineage.

Example result fields:

```text
run_id
experiment_id
instrument
signal_id
market_model_id
forward_horizon
sample_size
mean_return
median_return
hit_rate
mfe
mae
stability_score
oos_score
```

Component lineage may be stored separately:

```text
experiment_id
component_id
component_version
component_kind
timeframe
parameter_set_id
role
```

This avoids duplicating component metadata in every row.

---

# 15. Automated Analysis of Large Result Spaces

Manual inspection must not be the primary method of analysing large research spaces.

The Research domain should support automated analytical passes.

## 14.1 Screening

Automatically reject or flag experiments with:

- insufficient sample size,
- unstable results,
- weak out-of-sample behaviour,
- extreme parameter sensitivity,
- excessive concentration in one period,
- excessive concentration in one instrument,
- invalid temporal alignment,
- excessive complexity.

---

## 14.2 Marginal Contribution

The framework should compare nested models.

Example:

```text
Signal
Signal × Trend State 4h
Signal × Trend State 4h × Volatility Regime 1h
```

This measures whether an added condition creates real incremental value.

---

## 14.3 Family Analysis

Nearby variants should be grouped into Market Model or Strategy families.

Example family:

```text
Trend State 30m
Trend State 1h
Trend State 4h
Trend State 1h + Volatility Regime 30m
Trend State 4h + Volatility Regime 1h
```

Family analysis should evaluate:

- stability across nearby timeframes,
- stability across nearby parameters,
- component contribution,
- whether performance depends on one isolated optimum,
- cross-asset consistency.

---

## 14.4 Sensitivity Surfaces

Timeframe and parameter combinations should be summarised through matrices or surfaces.

Example:

```text
trend timeframe × volatility timeframe → research score
```

The purpose is to identify stable regions rather than one maximum point.

---

## 14.5 Multi-Objective Evaluation

A candidate should not be selected by one metric alone.

Possible dimensions:

```text
expectancy
stability
sample size
drawdown
complexity
out-of-sample performance
cross-asset consistency
execution sensitivity
```

The framework may use Pareto-frontier analysis or an explicit composite score.

---

## 14.6 Complexity Penalty

More complex models should require materially better and more stable evidence.

Conceptual score:

```text
adjusted_score
=
performance_score
- complexity_penalty
- instability_penalty
- multiple_testing_penalty
```

The exact formula belongs to Research Analytics configuration and should not be hard-coded globally.

---

# 16. Multiple Testing

Multitimeframe and parameter expansion increase false-discovery risk.

Every research run should preserve:

- number of generated candidates,
- number of evaluated candidates,
- number of rejected candidates,
- pruning rules,
- selection history,
- validation split definitions,
- family membership,
- ranking objective.

A top result among millions of tested combinations is not automatically evidence of an edge.

The framework must make the size of the search space visible.

---

# 17. Proposed Module Structure

Start with a minimal structure:

```text
src/trading_framework/market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Evolve only when the number and stability of components justify it:

```text
src/trading_framework/market_analysis/
├── features/
├── structures/
├── states/
├── engine/
├── graph/
├── registry/
├── cache/
├── alignment/
├── models/
└── protocols.py
```

Strategy definitions remain separate:

```text
src/trading_framework/strategy/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
├── occurrences/
└── protocols.py
```

The conceptual taxonomy is stable even if the directory structure evolves.

---

# 18. User Data Structure

```text
user_data/
├── development/
│   └── market_analysis/
├── candidates/
│   └── market_analysis/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategies/
└── research/
```

Working components may be used in experimental research when the result records:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

Mutable local model definitions require:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

---

# 19. Architectural Rules

1. Market Analysis owns reusable Features, Structures and States.
2. Market Models and Signal Models are declarative Strategy Domain compositions.
3. Both model types may consume the same Market Analysis outputs.
4. Models do not calculate analytical dependencies internally.
5. Models do not access arbitrary DataFrames or storage.
6. Controlled MarketFieldReferences are allowed.
7. Timeframe is part of analytical request and cache identity.
8. Source, computation and evaluation timeframe are distinct.
9. Resampling is explicit and reusable.
10. Higher-timeframe values use `available_at` semantics.
11. `LAST_CLOSED_BAR` is the default alignment policy.
12. Intrabar behaviour requires an explicit contract.
13. Multitimeframe is not a special model type.
14. Research supports Market Model only, Signal Model only and combined scope.
15. Single analytical hypotheses use one-condition models.
16. Lists do not imply logical `OR` or unrestricted Cartesian expansion.
17. Research spaces are bounded and observable.
18. Research progresses from small hypotheses to complete Strategy Models.
19. Market Analysis caches and Research Datasets are separate layers.
20. Large spaces require automated screening and multiple-testing metadata.
21. Working components and models used in research require fingerprints.
22. Batch/vectorized backtesting belongs to Research.
23. Replay, Paper and Live belong to Strategy Execution.
24. Every result preserves component, model, timeframe, parameter and dataset lineage.

---

# 20. Final Architectural Statement

The framework uses Market Analysis as a reusable language for describing market behaviour.

```text
Features describe measurable properties.

Structures describe market objects, levels, patterns and events.

States classify market conditions.

Market Models compose these outputs into market-context hypotheses.

Signal Models compose these outputs into trading-opportunity hypotheses.
```

Multitimeframe support is implemented through timeframe-aware analytical requests, explicit resampling dependencies and safe temporal alignment.

The framework must not rely on hidden informative-data decorators, monolithic Market Models or uncontrolled full-grid experimentation.

The intended flow is:

```text
Canonical Market Dataset
        ↓
Explicit Resampling DAG
        ↓
Market Analysis Outputs per Timeframe
        ↓
Safe Temporal Alignment
        ↓
Market Model / Signal Model Expression Trees
        ↓
Signal Research
        ↓
Automated Screening and Family Analysis
        ↓
Selected Strategy Research Space
```

This architecture preserves composability, computational reuse, research correctness and manageable analytical complexity.
