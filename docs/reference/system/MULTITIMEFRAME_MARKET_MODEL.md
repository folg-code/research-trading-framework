# Multitimeframe and Market Model Architecture — As-Built Reference

> Moved from `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` by
> Sprint 054 T004 (vision reclassification and reference layering). The
> sections below were classified **CURRENT** (or are the current-behavior
> portion of a section classified **MIXED**) against the codebase as of
> 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references — including the correction of the vision index's inaccurate
> whole-file "(future)" label. Content is reproduced verbatim from the
> vision document — this move does not rewrite any architectural decision.
>
> Future-facing, ambiguous-status, and not-yet-built content (Research-Space
> Growth details, Screening/Marginal-Contribution analysis, Sensitivity
> Surfaces, Multi-Objective/Pareto evaluation, the Complexity Penalty
> formula, the Proposed Module Structure, and the User Data Structure)
> remains in
> [`docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`](../../vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md).

---

## Core Decision

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

## Market Analysis Responsibilities

### Market Analysis Question

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

### Market Analysis Categories

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

### Features

> As-built note: ATR, RSI, MACD, stochastic, slope, relative volatility,
> range expansion, return distribution/autocorrelation, EMA distance,
> session range and level distance are all implemented. VWAP-based and
> volume-delta features named below returned zero matches in `src/` as of
> this sprint.

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

### Structures

> As-built note: swing structure (higher-high/lower-low) and session range
> are implemented as typed dataclasses. Fair value gap, liquidity sweep,
> order block, and liquidity pool named below returned zero matches in
> `src/` as of this sprint.

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

## Boundary Between Market Analysis and Strategy

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

## Market Model Definition

### Market Model Question

A Market Model answers:

```text
Which combination of analytical market conditions defines the context under study?
```

It does not calculate ATR, trend, volatility regime or market structure internally.

It consumes their previously calculated outputs.

---

### Market Model as Expression Tree

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

### Market Model Ownership

The Market Model Definition remains in the Strategy domain because it expresses a strategy-relevant market context.

The analytical algorithms used by the Market Model remain in Market Analysis.

Therefore:

```text
Market Analysis owns Features, Structures and States.
Strategy owns Market Model and Signal Model composition.
```

This prevents Market Analysis from becoming coupled to specific trading ideas.

---

### Market and Signal Models Must Remain Lightweight

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

## Multitimeframe Architecture

### Core Principle

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

### Timeframe Is Part of Component Identity

> As-built note: `market_analysis/identity/{computation.py,mtf.py}`
> implement component-identity hashing including timeframe, confirming the
> correct pattern (`ComponentId("volatility.state")`, not
> `VolatilityState30m`). The full 11-field identity list below is not
> literally reproduced as one dataclass — `resampling_policy`,
> `alignment_policy`, and `calendar_version` specifically returned zero
> matches in `src/` as of this sprint; the identity concept is built but
> narrower than the full dimension list proposed here.

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

### Source, Computation and Evaluation Timeframe

> As-built note: `market_analysis/models/request.py`'s `ComponentRequest`
> has `computation_timeframe` and a `resolved_computation_timeframe(...)`
> method; `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`'s
> "Multitimeframe Is a Property of Analytical Requests" section confirms
> `observed_at`/`available_at` semantics exist. The computation-timeframe
> distinction is concretely implemented; a distinct, separately-named
> **evaluation timeframe** field was not found as an implementation field
> as of this sprint — the three-way conceptual distinction is real but not
> fully reified as three separate fields in one contract.

The framework must distinguish three concepts.

#### Source Timeframe

The granularity of the source dataset.

Example:

```text
NQ 1m bars
```

#### Computation Timeframe

The granularity on which an analytical component is calculated.

Examples:

```text
Volatility Regime on 30m
Trend State on 1h
Market Phase on 4h
```

#### Evaluation Timeframe

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

## Resampling

### Resampling Is a Shared Dependency

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

### Resampling Contract

> As-built note: resampling logic exists and is reused across
> `market_analysis/` (see "Resampling Is a Shared Dependency" above). The
> literal `ResampleRequest`/`BoundaryPolicy` dataclass types below returned
> zero matches in `src/` as of this sprint — only the underlying resample
> function is implemented, not this specific contract shape.

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

## Temporal Alignment and Look-Ahead Protection

### Main Risk

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

### Default Alignment Policy

> As-built note: `observed_at`/`available_at` fields are pervasively
> implemented (`market_analysis/models/{alignment,outputs,result}.py`,
> `market_analysis/data/align.py`), directly realizing the "no early
> exposure" rule. The literal string `LAST_CLOSED_BAR` returned zero
> matches in `src/` as of this sprint — the named policy constant is not
> present verbatim, though the alignment module's default behavior is
> consistent with this rule.

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

### As-Of Alignment

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

### Observed Time and Available Time

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

## MarketFieldReference

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

## Market and Signal Model Examples

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

## Independent Alternatives (Research-Space Growth)

### Fixed Selection

One explicit model:

```yaml
trend_state:
  timeframe: 4h

volatility_regime:
  timeframe: 1h
```

This creates one Market Model definition.

---

### Independent Alternatives

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

## Research Result Architecture (current-behavior portion)

> As-built note: `research/datasets/{signal_research,strategy_research,predictive}.py`
> and `market_analysis/storage/workspace.py` implement clearly separated,
> distinctly-persisted layers matching most of the layer chain below;
> `strategy/signal_occurrence.py` confirms `SignalOccurrence` exists as its
> own type. Whether any code path ever builds the "one giant wide matrix"
> anti-pattern this section warns against was not independently verified —
> absence of an anti-pattern is not directly checkable via grep.

The framework should not create a separate wide DataFrame column for every complete experiment combination.

Avoid:

```text
rows = every market timestamp
columns = every Market Model × Signal Model × timeframe combination
```

This creates poor memory characteristics and difficult lineage.

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

### Market Analysis Cache

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

### Market Model Results

Boolean Market Model states may be represented as:

- boolean masks,
- bitsets,
- categorical arrays,
- integer state codes,
- sparse event tables where appropriate.

An experiment should reference reusable state identities rather than copy the entire time series.

---

### Research Results

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

## Family Analysis

> As-built note: `research/datasets/signal_research_family.py`,
> `research/signal_research/{family_planning,model_registry}.py`, and
> `application/signal_research/run_signal_research_family.py` implement a
> concrete Signal Research "family" concept (variant generation, bounded
> expansion, dedicated dataset). Full parity with every named evaluation
> dimension below (cross-asset consistency specifically) was not
> individually diffed.

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

## Multiple Testing

> As-built note: `research/signal_research/family_planning.py`'s
> `FamilyExperimentPlan` dataclass literally has `candidates_generated`,
> `candidates_evaluated`, `candidates_skipped`, and `skipped_variant_ids` —
> a near-verbatim implementation of the ask below, for the Signal Research
> family case specifically. Validation split definitions exist separately
> (`research/predictive/splitting.py`). Not confirmed: whether "selection
> history"/"ranking objective" metadata is preserved, or whether this
> extends beyond Signal Research family experiments to Strategy Research
> generally.

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

## Architectural Rules (current-behavior portion)

> As-built note: rules 1–13 below (Market Analysis / Market Model / Signal
> Model composition, timeframe-as-identity, resampling, temporal alignment)
> are CURRENT per the sections above. Rule 22 (batch/vectorized backtesting
> belongs to Research) is CURRENT. Rules 17, 20, 21, and 23 are left in
> `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §19 because they
> inherit MIXED/FUTURE findings (bounded/observable research spaces
> partially built; automated screening/multiple-testing metadata partially
> built; fingerprints for working components unbuilt; Replay/Live Execution
> unbuilt) — see
> `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §19.

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
19. Market Analysis caches and Research Datasets are separate layers.
22. Batch/vectorized backtesting belongs to Research.
24. Every result preserves component, model, timeframe, parameter and dataset lineage.

---

## Final Architectural Statement (current-behavior portion)

> As-built note: the timeframe-aware-request/resampling/temporal-alignment
> claim below (formerly the "line 1308" sentence flagged by the repo
> workflow audit) is well-supported by the sections above. The closing
> "intended flow" diagram in the vision document bundles this true
> statement together with "Automated Screening and Family Analysis" —
> Family Analysis is CURRENT for Signal Research (see above); generalized
> Screening is AMBIGUOUS (see
> `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §14.1).

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
