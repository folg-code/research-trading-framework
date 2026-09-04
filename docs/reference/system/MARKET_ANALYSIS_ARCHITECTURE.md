# Market Analysis Architecture — As-Built Reference

> Merged from the former `docs/reference/system/ARCHITECTURE_TECHNICAL.md`
> ("Market Analysis Architecture", "Market Analysis Engine") and the former
> `docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md` ("Market Analysis
> Responsibilities", "Market Analysis Categories", "Features", "Structures")
> by Sprint 055 T007, per the maintainer-approved merge in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. Per T001's dedup
> policy, the longer/more-complete version of each duplicated section is kept
> verbatim as the body, with genuinely unique material from the other copy
> appended — no paraphrasing. Both source files originated in `docs/vision/`
> and were moved into `docs/reference/` by Sprint 054 T002/T004; the CURRENT/
> MIXED as-built classification notes from that move are preserved below.
>
> Time, multitimeframe and alignment content (the other genuinely distinct
> subject these two source files carried) now lives in
> [`TIME_AND_ALIGNMENT.md`](TIME_AND_ALIGNMENT.md) — this file cross-references
> it rather than repeating it. Domain ownership and model composition
> (Market Model / Signal Model / Strategy Model / SignalOccurrence) live in
> [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md).

---

## Purpose

The Market Analysis Domain provides reusable, strategy-independent descriptions of market behaviour.

Its semantic taxonomy is:

```text
Market Analysis Components
├── Features
├── Structures
└── States
```

It replaces the previous `Technical Analysis` naming.

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

All categories may use the same Market Analysis Engine, dependency graph, cache and execution contracts. The categories express meaning and result shape. They do not require separate computation engines.

---

## Feature

> As-built note: ATR, RSI, MACD, stochastic, slope, relative volatility,
> range expansion, return distribution/autocorrelation, EMA distance,
> session range and level distance are all implemented. VWAP-based and
> volume-delta features named below returned zero matches in `src/` as of
> Sprint 054 T003.

A Feature represents a measurable or time-aligned analytical property.

Possible outputs:

```text
numeric value
boolean value
categorical value
series
vector-like result
```

Examples:

```text
ATR
VWAP
rolling volatility
RSI
slope
momentum
wick ratio
distance to session high
distance to VWAP
volume delta
```

A metric is one type of Feature. A separate top-level `Metrics` category is not required.

A Feature may be an input to another Feature, Structure or State component.

---

## Structure

> As-built note: swing structure (higher-high/lower-low) and session range
> are implemented as typed dataclasses. Fair value gap, liquidity sweep,
> order block, and liquidity pool named below returned zero matches in
> `src/` as of Sprint 054 T003.

A Structure represents an identified market object, level, pattern or event.

Examples:

```text
Pivot
Swing High
Swing Low
Higher High
Higher Low
Lower High
Lower Low
Session Range
Liquidity Level
Liquidity Sweep
Liquidity Pool
Fair Value Gap
Break of Structure
Order Block
```

Structures should use explicit typed schemas or typed structured datasets.

Unstructured dictionaries are not the default output type.

---

## Detectors, Classifiers and Transformations

`Detector` and `Classifier` describe implementation behaviour.

They are not top-level domain categories.

Examples:

```text
PivotDetector
    → Pivot Structure

LiquiditySweepDetector
    → LiquiditySweep Structure

TrendClassifier
    → Trend State
```

`Transformation` is also not a default top-level category.

Different transformations belong to different responsibilities:

```text
Provider normalization
    → Market Data

Resampling
    → explicit shared dependency or derived dataset

Returns calculation
    → Feature

Temporal alignment
    → Market Analysis Engine
```

A generic `transformations/` directory should not be introduced without a coherent responsibility.

---

## Component Contract

Every Market Analysis component declares:

```text
id
version or implementation fingerprint
parameters
dependencies
input requirements
output schema
timeframe requirements
alignment policy
cache policy
determinism assumptions
compute contract
```

Conceptual example:

```python
class AnalysisComponent(Protocol):
    @property
    def key(self) -> ComponentKey:
        ...

    @property
    def dependencies(self) -> tuple[ComponentRequest, ...]:
        ...

    def compute(
        self,
        context: AnalysisContext,
    ) -> AnalysisResult:
        ...
```

The exact API may evolve.

Explicit dependencies and output declarations are mandatory.

---

## Component Request

> As-built note: the actual `ComponentRequest`
> (`market_analysis/models/request.py`) has three fields
> (`component_id`, `parameters`, `computation_timeframe`) — a smaller
> contract than the illustrative version below. The core idea (an explicit,
> non-hidden request object) is implemented; the exact field set is not.

A timeframe-aware request may be represented as:

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

A simplified request may omit fields only when their semantics are unambiguous and preserved internally.

A decorator may provide syntax sugar but must resolve to explicit, inspectable and serializable metadata.

---

## MarketFieldReference

Model expressions must not access arbitrary raw DataFrames or storage objects.

Simple source-data conditions may use:

```text
MarketFieldReference
```

Example fields:

```text
open
high
low
close
volume
bid
ask
```

A controlled `MarketFieldReference` must preserve:

```text
dataset lineage
field identity
source timeframe
evaluation timeframe
available_at semantics
```

It participates in dependency resolution and temporal validation.

It must not become a bypass around repository or lineage rules.

---

## Market Analysis Engine

### Purpose

The Market Analysis Engine calculates reusable analytical components efficiently.

It supports:

- Features,
- Structures,
- States,
- dependency resolution,
- lazy execution,
- shared computation,
- caching,
- temporal alignment,
- deterministic reuse.

It is shared by:

- Signal Research,
- Strategy Research,
- Strategy Execution.

It does not own:

- Market Model definitions,
- Signal Model definitions,
- Strategy Model definitions,
- research interpretation.

### Engine Components

Suggested internal capabilities:

```text
Component Registry
Dependency Graph
Component Executor
Component Cache
Temporal Alignment
Result Materialization
```

These may initially live in a small module and be separated only when implementation scale justifies it.

### Component Registry

The registry maps:

```text
Component Key
    ↓
Component Factory or Implementation
```

Responsibilities:

- discovery,
- unique naming,
- version selection,
- parameter validation,
- dependency lookup,
- duplicate prevention,
- framework/user component loading.

Framework components may live in `src/`.

User components live in `user_data/`.

`src/` must never import concrete user modules directly.

### Dependency Graph

The engine builds a directed acyclic graph.

Example:

```text
MarketBar
   ├── ATR
   │    └── Volatility State
   │
   ├── Pivot Structure
   │    └── Trend State
   │
   └── Session Range
        └── Liquidity Sweep
```

The graph must:

- detect cycles,
- deduplicate equivalent nodes,
- resolve execution order,
- expose lineage,
- identify reusable outputs.

Hidden component calls inside `compute()` are prohibited.

### Lazy Execution

> As-built note: the dependency-planning architecture (`market_analysis/planning/`)
> structurally supports lazy resolution; an execution-time proof that
> unrelated components are skipped (rather than eagerly computed and
> discarded) was not independently traced.

The engine calculates only requested outputs and their transitive dependencies.

Unrelated components are not calculated.

Lazy execution is mandatory for large research spaces.

### Shared Computation

> As-built note: component identity (`component_id`, hashes) is pervasively
> implemented, supporting dedup. A cross-consumer cache-hit path (e.g. a
> Signal Research run reusing a Strategy Research run's cached node) was not
> independently traced end-to-end.

A unique deterministic node is calculated once per computation identity.

Example:

```text
ATR(
    dataset=NQ_1m_v3,
    period=14,
    computation_timeframe=1h,
    evaluation_timeframe=1m,
    alignment_policy=LAST_CLOSED_BAR,
)
```

This result may be reused by:

- Market Models,
- Signal Models,
- Exit Models,
- Signal Research,
- Strategy Research,
- Strategy Execution.

### Cache Identity

The cache key includes all material inputs.

Suggested dimensions:

```text
component_id
component_version or implementation_hash
parameters
dataset_id
dataset_version
instrument
time_range
source_timeframe
computation_timeframe
evaluation_timeframe
resampling_policy
alignment_policy
calendar_version
dependency_versions or hashes
framework_version
```

A cached result must not be reused when any material input differs.

### Temporal Alignment

The engine's default higher-timeframe policy is `LAST_CLOSED_BAR`, applied via backward as-of semantics. Full semantics — the look-ahead risk, the default policy, `observed_at`/`available_at`, and what the executor does and does not enforce (G-04) — live in [`TIME_AND_ALIGNMENT.md`](TIME_AND_ALIGNMENT.md); this section states only the engine-scoped fact that alignment is a first-class engine responsibility, not something a component implements privately.

### Output Forms

> As-built note: Feature and Structure output forms are confirmed. State
> output forms inherit the caveat that the State category is the least
> built of the three (see `docs/vision/ARCHITECTURE_TECHNICAL.md` §4.4).

Outputs should preserve their natural structure.

Features may use:

```text
Series
DataFrame columns
typed categorical arrays
```

Structures may use:

```text
typed records
event tables
structured datasets
```

States may use:

```text
categorical arrays
boolean masks
typed state records
```

A common metadata wrapper may be used without forcing every payload into one scalar column.

### Execution Context

An `AnalysisContext` provides controlled access to:

- source dataset,
- resolved dependencies,
- MarketFieldReferences,
- time model,
- calendar,
- parameters,
- execution metadata.

Components must not:

- access global state,
- open arbitrary files,
- instantiate providers,
- access brokers,
- trigger hidden resampling.

### Market Analysis Engine Rules

> As-built note: rule 12 ("Working components used in research require
> fingerprints") inherits the FUTURE status of
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §5.12 "Local Development and
> Promotion" — the fingerprint fields it requires do not exist in `src/`.
>
> **G-04 (added Sprint 055 T007, newly-authored per D-S055-04):** rule 8
> below ("Higher-timeframe alignment uses legal availability semantics")
> describes alignment behaviour, not executor enforcement. S049-T001
> verified line-by-line that the executor does **not** enforce
> inference-time `available_at` rejection today (`executor.py`,
> `planner.py`, `assembler.py` — no such mechanism exists; see
> `ROADMAP.md` §13F and `docs/adr/README.md`'s **ADR-0030 — Inference-Time
> Availability Enforcement (PLANNED)**). Alignment honours `available_at`
> for batch multitimeframe joins; nothing today stops a component from
> reading data before its legal availability at inference time. See
> [`TIME_AND_ALIGNMENT.md`](TIME_AND_ALIGNMENT.md) for the full as-built
> distinction.

1. Features, Structures and States are the semantic output categories.
2. Every component declares dependencies.
3. The graph is acyclic.
4. Execution is lazy.
5. Equivalent nodes are deduplicated.
6. Cache identity includes all material temporal inputs.
7. Resampling is explicit and reusable.
8. Higher-timeframe alignment uses legal availability semantics (batch alignment only — see the G-04 note above for the executor gap).
9. Complex outputs use typed schemas.
10. Components do not own strategy decisions.
11. User components are loaded through controlled discovery.
12. Working components used in research require fingerprints.
