# AGENTS_MULTITIMEFRAME_MARKET_MODEL.md

# Multitimeframe, Market Analysis and Model Composition Contract

## 1. Purpose

This file defines mandatory rules for AI coding agents working on:

- Market Analysis,
- Market Analysis,
- Market Models,
- Market Analysis Engine,
- resampling,
- multitimeframe alignment,
- Signal Research,
- large research spaces.

The agent must read this file together with:

1. `ARCHITECTURE_FOUNDATIONS.md`
2. `ARCHITECTURE_TECHNICAL.md`
3. `WORKFLOWS_AI_ADR.md`
4. `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`
5. relevant contracts, tests and ADRs

This contract overrides implementation convenience.

---

# 2. Domain Ownership

The agent must preserve:

```text
Market owns normalized market facts.

Market Analysis owns reusable Features, Structures and States.

Strategy owns Market Model, Signal Model and Strategy Model definitions.

Research owns experiment orchestration, datasets and analytics.

Execution Domain owns runtime market interaction; the workflow is named Strategy Execution.
```

The agent must not move responsibilities between these domains without an explicit architectural decision.

---

# 3. Market Analysis Contract

Market Analysis contains:

```text
Features
Structures
States
```

## Features

Features calculate numerical, categorical or time-series outputs.

Examples:

- ATR,
- VWAP,
- rolling volatility,
- slope,
- momentum,
- distance measures.

## Structures

Structures calculate typed market objects or events.

Examples:

- swing structure,
- fair value gap,
- session range,
- liquidity sweep,
- order block.

## States

States classify reusable market conditions.

Examples:

- trend state,
- volatility regime,
- momentum state,
- liquidity state,
- structural state,
- market phase.

The agent must not implement strategy-specific intent inside Market Analysis.

Forbidden examples:

```text
good_for_london_sweep
allow_long_entry
avoid_short_trade
preferred_breakout_context
```

Allowed examples:

```text
trend = bullish
volatility = high
structure = ranging
liquidity = compressed
```

---

# 4. Market and Signal Model Contract

Market Models and Signal Models are declarative expressions over Market Analysis outputs.

It is not a Component implementation.

It is not a calculation engine.

It must not:

- load data,
- open files,
- resample data,
- calculate indicators,
- calculate Structures,
- calculate Market Analysis states,
- access providers,
- access storage directly,
- generate Signals,
- determine Exits,
- calculate Risk.

A Market Model or Signal Model may:

- reference Component Requests,
- define comparison conditions,
- combine conditions with explicit logical operators,
- preserve component lineage,
- evaluate an expression over resolved results.

Expected conceptual forms:

```python
MarketModelDefinition(id=..., version=..., expression=And(...))
SignalModelDefinition(id=..., version=..., expression=And(...))
```

A Signal Model produces a provider-independent `SignalOccurrence` owned by the Strategy Domain.

---

# 5. MarketFieldReference Contract

Models must not access arbitrary DataFrames or storage objects.

Simple source-data conditions may use a controlled `MarketFieldReference`.

It must preserve:

```text
dataset lineage
field identity
source timeframe
evaluation timeframe
available_at semantics
```

It must participate in dependency resolution and temporal validation.

---

# 6. Signal Research Scope Contract

Signal Research supports:

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

The scope must be explicit.

A single analytical hypothesis is represented through a one-condition Market Model or Signal Model.

---

# 7. Multitimeframe Contract

Multitimeframe is represented through timeframe-aware analytical requests.

The agent must not introduce a separate multitimeframe Strategy or Market Model type unless a proven requirement cannot be represented by normal composition.

Correct:

```text
Trend State 4h
Volatility Regime 1h
Structural State 30m
Signal 1m
```

Incorrect:

```text
SpecialMultiTimeframeMarketModel
```

unless the type adds a real domain capability rather than wrapping ordinary requests.

---

# 8. Timeframe Identity Rules

Every timeframe-dependent calculation must include timeframe in its identity.

A cache or node identity must include all material inputs, including where relevant:

```text
component_id
component_version
parameters
dataset_id
dataset_version
instrument
source_timeframe
computation_timeframe
evaluation_timeframe
resampling_policy
alignment_policy
calendar_version
framework_version
```

The agent must never reuse a cached result when any material identity input differs.

---

# 9. Source, Computation and Evaluation Timeframe

The agent must distinguish:

```text
source timeframe
computation timeframe
evaluation timeframe
```

Example:

```text
source data:         NQ 1m
trend calculation:  4h
signal evaluation:  1m
```

The agent must not collapse these fields into one ambiguous `timeframe` when the distinction affects correctness.

A simplified API may expose one field only when source and evaluation semantics are unambiguous and preserved internally.

---

# 10. Resampling Rules

Resampling is an explicit dependency-graph node or dataset transformation.

The agent must not hide resampling inside:

- ATR,
- Trend State,
- Volatility Regime,
- Market Model,
- Signal Model,
- arbitrary helper functions.

Shared resampled datasets must be reused.

Example:

```text
NQ 1m
  └── Resample 1h
        ├── ATR 1h
        ├── Trend State 1h
        └── Volatility Regime 1h
```

The agent must not independently resample NQ 1m to 1h three times for these consumers.

---

# 11. Temporal Alignment Rules

The default higher-timeframe policy is:

```text
LAST_CLOSED_BAR
```

A higher-timeframe result must not be visible before its underlying interval closes and the result becomes available.

Every temporal result must preserve or allow derivation of:

```text
observed_at
available_at
```

The agent must use backward as-of semantics or an equivalent correct mechanism when aligning higher-timeframe results to lower-timeframe evaluation points.

Forbidden:

- joining final higher-timeframe values to timestamps inside the still-open interval,
- blind forward-fill without availability semantics,
- using a final 4h high, low, close or state before the 4h bar closes,
- silently changing bar timestamp conventions.

---

# 12. Intrabar Rules

Partial higher-timeframe bars are allowed only through an explicit intrabar component contract.

An intrabar component must declare:

- partial-bar input requirements,
- update frequency,
- availability semantics,
- research/live parity assumptions,
- cache identity,
- output stability rules.

The agent must not introduce partial-bar behaviour as an optimization or shortcut.

---

# 13. Decorator Rules

A decorator may be used only as optional syntax sugar.

A decorator must resolve to explicit, inspectable and serializable metadata.

It must not hide:

- component dependencies,
- timeframe,
- resampling policy,
- alignment policy,
- warm-up requirements,
- cache identity,
- component lineage.

Do not implement a Freqtrade-like informative decorator as the core architecture.

---

# 14. Component Dependency Rules

Every Market Analysis component must declare:

```text
id
version
parameters
dependencies
input requirements
output schema
timeframe requirements
cache policy
determinism assumptions
```

Dependencies must be visible before execution.

Hidden Component calls inside `compute()` are prohibited.

The dependency graph must remain acyclic.

Each unique deterministic node is calculated once per computation identity.

---

# 15. Research Space Rules

The agent must distinguish:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

A list does not automatically mean logical `OR`.

A list does not automatically mean a full Cartesian product.

The agent must not implement unbounded expansion as the default.

Before executing a research space, the planner should expose where possible:

```text
number_of_candidates
number_of_unique_dependencies
number_of_reused_nodes
number_of_new_nodes
estimated_output_size
applied_constraints
```

---

# 16. Research Constraint Rules

Research configuration should support constraints such as:

```text
maximum Market Model conditions
maximum distinct timeframes
allowed timeframe ordering
allowed component categories
forbidden duplicate component roles
maximum parameter dimensions
maximum candidate count
```

Invalid or prohibited combinations should be pruned before expensive computation.

The agent must not generate every mathematically possible combination when domain constraints can eliminate meaningless cases.

---

# 17. Research Methodology Rules

The preferred progression is:

```text
individual components
        ↓
pairwise interactions
        ↓
small Market Model compositions
        ↓
complete Strategy Research
        ↓
robustness validation
```

The agent should not default to testing:

```text
all Market Analysis components
× all timeframes
× all parameters
× all Signals
× all Exits
× all Risk Models
```

A large full-grid search requires explicit user configuration and visible multiple-testing metadata.

---

# 18. Result Storage Rules

The agent must separate:

```text
Market Analysis Cache
Market Analysis Results
Market Model States
Signal Research Dataset
Strategy Research Dataset
Analytics
```

Do not store every complete experiment as a duplicated full DataFrame.

Prefer reusable identities and references.

Component data may be stored in a wide computation-friendly format.

Research results should use queryable fact tables with explicit lineage.

Required lineage includes where applicable:

```text
run_id
experiment_id
dataset_id
dataset_version
component_id
component_version
component_kind
timeframe
parameter_set_id
market_model_id
signal_id
execution assumptions
framework version
```

---

# 19. Analytics Rules

For large result spaces, the agent should implement or preserve support for:

- minimum sample-size filtering,
- stability analysis,
- out-of-sample evaluation,
- marginal contribution analysis,
- family analysis,
- parameter sensitivity,
- timeframe sensitivity,
- cross-asset consistency,
- complexity metrics,
- multiple-testing metadata.

The agent must not label the highest-scoring candidate as validated solely because it ranks first.

---

# 20. Complexity Rules

Every Market Model should expose measurable complexity.

Possible complexity dimensions:

```text
number of conditions
number of distinct analytical components
number of distinct timeframes
number of free parameters
expression-tree depth
```

Research Analytics may apply complexity penalties.

The agent must not hard-code one universal penalty formula into the domain layer.

---

# 21. Module Placement Rules

Framework Market Analysis code:

```text
src/trading_framework/market_analysis/
```

Initial minimal structure:

```text
market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Framework model contracts and generic composition:

```text
src/trading_framework/strategy/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
└── occurrences/
```

User working components:

```text
user_data/development/market_analysis/
```

Candidate components:

```text
user_data/candidates/market_analysis/
```

Proprietary definitions:

```text
user_data/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
└── strategies/
```

`src/` must never import concrete `user_data` modules.

---

# 22. Testing Requirements

Every multitimeframe implementation must include tests for:

## Unit Tests

- timeframe value objects,
- Component Request identity,
- cache-key differences by timeframe,
- Market Model expression evaluation,
- explicit dependency declarations,
- cycle detection,
- research-space constraints.

## Temporal Tests

- last closed higher-timeframe value,
- no access to incomplete higher-timeframe bar,
- correct `available_at`,
- daylight-saving transitions where relevant,
- session boundaries,
- holiday and shortened-session behaviour,
- source/computation/evaluation timeframe distinction.

## Resampling Tests

- OHLC aggregation,
- volume aggregation,
- empty intervals,
- market closures,
- boundary policy,
- derived dataset lineage.

## Regression Tests

Every fixed look-ahead or alignment bug requires a regression test.

## Research Tests

- lists are not confused with logical expressions,
- constrained candidate counts are correct,
- repeated dependencies are deduplicated,
- family lineage is preserved,
- analytics does not trigger unnecessary recomputation.

---

# 23. Error Handling Rules

The agent must fail explicitly when:

- timeframe conversion is invalid,
- alignment policy is missing,
- a higher-timeframe value has no legal `available_at`,
- a component dependency is unresolved,
- a dependency cycle exists,
- source data cannot support the target timeframe,
- resampling rules are ambiguous,
- research expansion exceeds configured limits,
- cached data identity is incompatible.

Do not silently:

- forward-fill invalid values,
- substitute a different timeframe,
- ignore incomplete intervals,
- drop failed combinations,
- reuse stale caches,
- reduce the requested search space without metadata.

---

# 24. Prohibited Designs

The agent must not introduce:

1. a Market Model that calculates indicators internally,
2. a Market Model that opens market-data files,
3. a Market Model that resamples data internally,
4. a special multitimeframe strategy god object,
5. hidden informative dataframes,
6. final higher-timeframe values available before bar close,
7. one full copied DataFrame per experiment,
8. automatic unrestricted Cartesian-product expansion,
9. Market Analysis components named after strategy-specific intent,
10. rankings treated as validation,
11. duplicated resampling for each consumer,
12. cache keys that omit timeframe or alignment semantics,
13. naive datetimes,
14. direct imports from concrete `user_data` modules into `src`.

---

# 25. Completion Checklist

Before completing a task in this area, verify:

```text
[ ] Market Model remains a declarative composition
[ ] Analytical logic belongs to Market Analysis
[ ] Market Analysis output is strategy-independent
[ ] Timeframe is explicit
[ ] Source, computation and evaluation timeframe are correctly represented
[ ] Resampling is explicit and reusable
[ ] Higher-timeframe alignment uses legal availability semantics
[ ] No incomplete-bar look-ahead exists
[ ] component dependencies are declared
[ ] Shared nodes are deduplicated
[ ] Cache identity includes all material temporal inputs
[ ] Research expansion is bounded and observable
[ ] Full Cartesian product is not implicit
[ ] Result lineage includes components and timeframes
[ ] Large result spaces support automated analysis
[ ] Tests cover temporal alignment and look-ahead
[ ] src/user_data boundary is preserved
[ ] Documentation is updated
```

---

# 26. Final Agent Rule

The target architecture is:

```text
Market Data
    ↓
Explicit Resampling Dependencies
    ↓
Market Analysis per Timeframe
    ├── Features
    ├── Structures
    └── States
            ↓
Safe Temporal Alignment
            ↓
Market Model / Signal Model Expressions
            ↓
Signal Research / Strategy Research
            ↓
Persistent Results and Automated Analytics
```

Agents must optimize this flow without hiding dependencies, weakening temporal correctness or collapsing domain boundaries.
