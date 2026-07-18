# Trading Research Framework

# ARCHITECTURE_TECHNICAL.md

## 1. Purpose

This document defines the technical architecture of the Trading Research Framework.

It translates the architectural foundations into implementation rules for:

- Time Model,
- Market Data Architecture,
- Market Analysis Engine,
- Event System,
- Configuration Architecture,
- Module Structure,
- Framework and User Space separation.

It must be treated as a technical contract for:

- framework maintainers,
- contributors,
- strategy developers,
- research users,
- AI coding agents.

This document must remain consistent with:

- `ARCHITECTURE_FOUNDATIONS.md`,
- `WORKFLOWS_AI_ADR.md`,
- domain-specific documentation,
- accepted ADRs.

The architecture preserves the boundary between:

```text
Reusable Framework
```

and:

```text
Private User Research Know-How
```

Framework implementation belongs to:

```text
src/
```

User-owned data, local working components, proprietary models and research outputs belong to:

```text
user_data/
```

---

# 2. Time Model

## 2.1 Purpose

The Time Model defines how the framework represents, normalizes, compares and interprets time.

Time handling affects:

- market data normalization,
- sessions,
- holidays,
- trading calendars,
- daylight saving time,
- futures contract rolls,
- Market Analysis,
- multitimeframe alignment,
- research,
- replay,
- Strategy Execution,
- reproducibility,
- look-ahead protection.

Time rules must be explicit.

No module may introduce an independent timezone convention.

---

## 2.2 Timestamp Policy

All internal timestamps must be timezone-aware.

The canonical internal representation is:

```text
UTC
```

Correct:

```python
datetime(..., tzinfo=timezone.utc)
```

Incorrect:

```python
datetime(...)
```

Every timestamp entering the framework must be normalized before it reaches domain logic.

---

## 2.3 Timezone Policy

The framework follows:

```text
UTC internally
Local or exchange time only at boundaries
```

Boundaries include:

- provider adapters,
- broker adapters,
- user interfaces,
- reports,
- exchange calendar definitions,
- configuration files.

Provider-specific timestamps must be converted to UTC during normalization.

The original timezone and conversion assumptions should be retained in metadata where relevant.

---

## 2.4 Trading Sessions

A Trading Session is a configuration-driven time abstraction.

Suggested fields:

```text
id
name
timezone
start_time
end_time
weekdays
calendar_id
breaks
holiday_policy
```

Examples:

```text
Asia
London
New York
CME RTH
CME ETH
```

A Trading Session defines when a session exists.

It does not calculate:

- session high,
- session low,
- session midpoint,
- session range,
- session sweep.

These are Market Analysis outputs.

Rule:

```text
Time Model:
When does the session exist?

Market Analysis:
What happened during the session?
```

Hard-coded session-hour checks inside analytical components are prohibited.

---

## 2.5 Trading Calendars

A Trading Calendar defines when a market is open.

Responsibilities include:

- trading days,
- weekends,
- holidays,
- shortened sessions,
- exchange closures,
- daylight saving transitions,
- session exceptions.

Examples:

```text
CME Calendar
NYSE Calendar
NASDAQ Calendar
Crypto 24/7 Calendar
Forex Calendar
```

The calendar abstraction must remain provider-independent.

External calendar libraries may be used behind adapters.

Domain and application code depend on framework contracts.

---

## 2.6 Holidays

Holiday rules must be explicit and versionable.

They affect:

- expected market closures,
- missing-range detection,
- data completeness,
- session duration,
- resampling boundaries,
- research assumptions,
- Strategy Execution availability.

A known market closure must not be classified as missing data.

Holiday logic belongs to the calendar layer, not to analytical feature code.

---

## 2.7 Futures Contract Rolls

The framework distinguishes:

```text
Contract Dataset
```

from:

```text
Continuous Futures Dataset
```

Examples:

```text
NQM26
NQU26
NQ Continuous
```

Contract-roll metadata should include:

```text
source_contract
destination_contract
roll_timestamp
roll_policy
roll_trigger
adjustment_method
adjustment_value
construction_version
```

Roll logic must not be hidden inside provider adapters.

Continuous futures are explicit derived datasets.

---

## 2.8 Clock Abstraction

Time-dependent application and Strategy Execution logic depend on a `Clock` contract.

Conceptual example:

```python
class Clock(Protocol):
    def now(self) -> datetime:
        ...
```

Possible implementations:

```text
SystemClock
FixedClock
ResearchClock
ReplayClock
```

Direct use of `datetime.now()` inside domain and application logic is forbidden.

---

## 2.9 Observed Time and Available Time

Temporal analytical outputs must preserve or allow derivation of:

```text
observed_at
available_at
```

`observed_at` identifies the market interval or event being described.

`available_at` identifies when the output may legally be consumed.

This distinction is mandatory for:

- multitimeframe alignment,
- look-ahead prevention,
- replay consistency,
- research/runtime parity.

---

## 2.10 Time Model Rules

1. UTC is the canonical internal timezone.
2. Naive datetimes are forbidden.
3. Provider and broker time is normalized at boundaries.
4. Sessions are configuration-driven.
5. Calendars own market-open and holiday logic.
6. Market Analysis consumes session definitions but does not define global time policy.
7. Futures contract rolls are explicit and versioned.
8. Time-dependent logic uses a Clock abstraction.
9. Dataset and analytical metadata preserve time assumptions.
10. Temporal outputs preserve legal availability semantics.
11. Higher-timeframe final values must not be visible before bar close.
12. Time semantics must be reproducible across Research and Strategy Execution.

---

# 3. Market Data Architecture

## 3.1 Purpose

The Market Data Architecture defines how market facts are:

- acquired,
- imported,
- normalized,
- validated,
- stored,
- versioned,
- published,
- accessed,
- replayed,
- reused.

The Market Domain owns trusted, provider-independent market facts and dataset contracts.

Infrastructure implements concrete providers, importers and storage adapters.

---

## 3.2 Supported Data Sources

Possible sources include:

- exchange APIs,
- broker APIs,
- market data vendors,
- local files,
- databases,
- historical archives,
- live streams.

Examples:

```text
Binance
Rithmic
MetaTrader 5
Databento
CSV
Parquet
DuckDB
```

Provider-specific schemas must not leak into domain, Market Analysis, Strategy or Research logic.

---

## 3.3 Provider and Importer Contracts

Provider contracts may include:

```text
HistoricalDataProvider
LiveDataProvider
InstrumentProvider
MetadataProvider
```

Importer contracts may include:

```text
DatasetImporter
ImportInspector
SourceReader
```

Provider API access and external file import are separate use cases.

They may reuse normalization logic but must not be represented by one ambiguous contract.

---

## 3.4 Data Normalization

Normalization converts provider-specific representations into canonical Market Domain models.

Examples:

```text
Provider Bar
    ↓
MarketBar
```

```text
Provider Trade
    ↓
MarketTrade
```

```text
Provider Quote
    ↓
MarketQuote
```

Normalization includes:

- field mapping,
- symbol mapping,
- timestamp conversion,
- timezone normalization,
- numeric normalization,
- precision normalization,
- volume normalization,
- side mapping,
- missing-field policy.

Normalization occurs before data reaches Market Analysis, Strategy, Research or Execution logic.

---

## 3.5 Instrument Mapping

Research instruments and execution instruments may differ.

Examples:

```text
NQ → NAS100
ES → US500
```

Instrument mapping must be explicit.

It must not be inferred from similar symbol strings.

Mappings belong to user-owned configuration or metadata.

---

## 3.6 Data Validation

Validation categories include:

### Schema Validation

- required fields,
- types,
- nullability,
- ranges,
- precision.

### Temporal Validation

- timestamp ordering,
- duplicates,
- gaps,
- timezone correctness,
- session consistency.

### Market Validation

- OHLC invariants,
- non-negative volume,
- valid bid/ask relationship,
- valid instrument identity.

### Dataset Validation

- requested coverage,
- expected sessions,
- holidays,
- contract lifecycle,
- missing partitions,
- metadata consistency,
- checksums,
- row counts.

Invalid data must not silently enter canonical datasets.

Validation summaries should be persisted.

---

## 3.7 Missing Data

Missing-data handling must distinguish:

```text
Unexpected Gap
```

from:

```text
Expected Market Closure
```

Trading Calendars are required for gap evaluation.

Supported policies may include:

```text
FAIL
WARN
MARK_INCOMPLETE
FETCH_MISSING
ACCEPT_KNOWN_CLOSURE
```

Market prices must not be forward-filled by default.

---

## 3.8 Historical Storage

Primary historical analytical storage:

```text
Apache Parquet
```

Reasons:

- columnar format,
- compression,
- partitioning,
- projection pushdown,
- predicate pushdown,
- Polars compatibility,
- DuckDB compatibility,
- low operational complexity.

PostgreSQL may store:

- metadata,
- dataset registry records,
- research run metadata,
- execution records,
- configuration metadata.

It is not the default primary store for large historical market datasets.

---

## 3.9 Storage Layers

Suggested logical layout:

```text
user_data/data/
├── source/
├── working/
├── normalized/
├── derived/
├── cache/
└── metadata/
```

### source

Original external archive when retention policy requires it.

### working

Temporary ingestion and transformation artifacts.

### normalized

Canonical provider-specific or source-specific market facts.

### derived

Datasets built from other datasets, including:

- resampled bars,
- continuous futures,
- adjusted series,
- reconstructed bars.

### cache

Reusable computational artifacts where appropriate.

### metadata

Dataset manifests, validation results, checksums and lineage.

---

## 3.10 Partitioning

Partitioning depends on data volume, update pattern and query pattern.

Suggested defaults:

| Data Type | Default Partitioning |
|---|---|
| Intraday bars | month |
| Daily bars | year or one file |
| Trades / ticks | day |
| Quotes | day |
| DOM / L2 | day or hour |
| Live working data | batches within day |
| Continuous futures bars | month |

Finalized layouts must avoid excessive small files.

Compaction converts working batches into stable partitions.

---

## 3.11 Dataset Identity

A Dataset is not a file path.

Its identity should include where relevant:

```text
dataset_id
version
provider
source_id
instrument
contract_id
data_type
timeframe
time_range
timezone
calendar
schema_version
normalization_version
validation_status
lifecycle_status
checksum
lineage
```

A material semantic change creates a new dataset version.

---

## 3.12 Dataset Lifecycle

Supported lifecycle states:

```text
WORKING
FINALIZED
PUBLISHED
INVALID
SUPERSEDED
```

Transitions are explicit:

```text
WORKING → FINALIZED → PUBLISHED
```

`finalize()` and `publish()` are separate responsibilities.

### FINALIZED

The dataset or partition has been:

- ordered,
- deduplicated,
- validated,
- checksummed,
- closed for normal writes.

### PUBLISHED

The dataset version is stable and available for Research or Replay Execution.

A combined workflow such as:

```text
finalize_and_publish()
```

may exist, but it must record both transitions explicitly.

A published dataset version is immutable.

---

## 3.13 Dataset Access

Consumers access market data through framework contracts.

Suggested contracts:

```text
MarketDataRepository
DatasetRepository
HistoricalDataFeed
LiveDataFeed
DatasetRegistry
```

Research, Strategy and Market Analysis components must not open Parquet files directly.

This preserves:

- storage independence,
- testability,
- lineage,
- caching,
- validation,
- version control.

---

## 3.14 Research Data Rule

Research consumes an explicit published reference:

```text
DatasetRef(dataset_id, version)
```

Research must not silently:

- download missing data,
- refresh remote data,
- mutate a dataset,
- substitute a newer dataset version,
- access working data as reproducible input.

Preferred flow:

```text
Data Preparation
      ↓
Published DatasetRef
      ↓
Research Run
```

---

## 3.15 Live Ingestion

Live ingestion flow:

```text
Live Provider
    ↓
Provider Adapter
    ↓
Normalization
    ↓
Minimal Validation
    ↓
Normalized Market Stream
    ├── Market Analysis Runtime
    ├── Strategy Runtime
    ├── Paper Execution
    ├── Monitoring
    └── Storage Recorder
```

Storage is an independent consumer.

Slow storage must not block the primary runtime path.

---

## 3.16 Replay

Replay exposes published historical data through runtime-compatible event contracts.

```text
Published Dataset
    ↓
Replay Query
    ↓
Replay Clock
    ↓
Ordered Market Events
    ↓
Runtime Consumers
```

Replay Execution is distinct from batch or vectorized backtesting.

```text
Batch / Vectorized Backtest
    → Research

Replay / Paper / Live
    → Execution
```

---

## 3.17 Market Data Architecture Rules

1. Provider schemas never leak into domain logic.
2. Provider API access and file import are separate use cases.
3. Bars may be provider-supplied or derived.
4. Historical storage uses Parquet by default.
5. Dataset identity is independent from storage path.
6. Dataset lifecycle is explicit.
7. Finalization and publication are separate.
8. Published dataset versions are immutable.
9. Research uses explicit published DatasetRefs.
10. Research does not trigger hidden downloads or mutations.
11. Calendars are used for gap detection.
12. Raw retention is policy-driven.
13. Futures contract identity is preserved.
14. Continuous futures are derived and lineage-aware.
15. Live storage does not block runtime processing.

---

# 4. Market Analysis Architecture

## 4.1 Purpose

The Market Analysis Domain provides reusable, strategy-independent descriptions of market behaviour.

Its semantic taxonomy is:

```text
Market Analysis Components
├── Features
├── Structures
└── States
```

It replaces the previous `Technical Analysis` naming.

---

## 4.2 Feature

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
slope
wick ratio
distance to session high
distance to VWAP
volume delta
```

A metric is one type of Feature.

A separate top-level `Metrics` category is not required.

---

## 4.3 Structure

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
Fair Value Gap
Break of Structure
Order Block
```

Structures should use explicit typed schemas or typed structured datasets.

Unstructured dictionaries are not the default output type.

---

## 4.4 State

A State represents a market classification at a given time.

Examples:

```text
trend = bullish
market_regime = ranging
volatility = expanding
momentum = weakening
structure = continuation
liquidity = compressed
```

States may depend on:

- Market Data,
- Features,
- Structures,
- time abstractions,
- sessions,
- calendars.

Example:

```text
Pivot Structures
+ Slope Feature
+ Volatility Feature
        ↓
Trend / Range State
```

---

## 4.5 Detectors, Classifiers and Transformations

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

## 4.6 Component Contract

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

## 4.7 Component Request

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

## 4.8 MarketFieldReference

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

# 5. Market Analysis Engine

## 5.1 Purpose

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

---

## 5.2 Engine Components

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

---

## 5.3 Component Registry

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

---

## 5.4 Dependency Graph

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

---

## 5.5 Lazy Execution

The engine calculates only requested outputs and their transitive dependencies.

Unrelated components are not calculated.

Lazy execution is mandatory for large research spaces.

---

## 5.6 Shared Computation

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

---

## 5.7 Cache Identity

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

---

## 5.8 Temporal Alignment

The default higher-timeframe policy is:

```text
LAST_CLOSED_BAR
```

Higher-timeframe results are aligned using backward as-of semantics or an equivalent correct mechanism:

```text
use the latest result whose available_at <= evaluation timestamp
```

Blind forward-fill without availability semantics is prohibited.

---

## 5.9 Intrabar Components

Partial higher-timeframe data is allowed only through an explicit intrabar contract.

Such a component declares:

```text
partial interval input
update frequency
available_at policy
research/runtime parity assumptions
cache identity
output stability policy
```

Intrabar behaviour must never arise accidentally from ordinary resampling.

---

## 5.10 Output Forms

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

---

## 5.11 Execution Context

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

---

## 5.12 Local Development and Promotion

Local working components may live under:

```text
user_data/development/market_analysis/
```

Validated candidates may live under:

```text
user_data/candidates/market_analysis/
```

Promoted framework components live under:

```text
src/trading_framework/market_analysis/
```

Working components used in research must preserve:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

Formal versioning begins when a component becomes part of the maintained framework contract.

---

## 5.13 Market Analysis Engine Rules

1. Features, Structures and States are the semantic output categories.
2. Every component declares dependencies.
3. The graph is acyclic.
4. Execution is lazy.
5. Equivalent nodes are deduplicated.
6. Cache identity includes all material temporal inputs.
7. Resampling is explicit and reusable.
8. Higher-timeframe alignment uses legal availability semantics.
9. Complex outputs use typed schemas.
10. Components do not own strategy decisions.
11. User components are loaded through controlled discovery.
12. Working components used in research require fingerprints.

---

# 6. Model Composition Architecture

## 6.1 Market Model

A Market Model is a declarative expression over Market Analysis outputs.

It may reference:

- Features,
- Structures,
- States,
- controlled MarketFieldReferences,
- logical operators,
- comparison operators.

It must not:

- load data,
- calculate components internally,
- resample data,
- access storage,
- access providers,
- generate orders.

---

## 6.2 Signal Model

A Signal Model follows the same implementation pattern.

It is a declarative expression over Market Analysis outputs.

It produces a provider-independent:

```text
SignalOccurrence
```

The Strategy Domain owns the SignalOccurrence model.

Suggested fields:

```text
signal_model_id
signal_model_version or definition_hash
instrument
detected_at
direction
reference_price
strength
analytical_lineage
```

Research and Execution may add workflow metadata but must not redefine the core semantics.

---

## 6.3 Strategy Model

A Strategy Model composes:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

Position sizing remains part of the Risk Model in Version 1.

Exit and Risk Models are contract-based components.

They may use declarative conditions and deterministic calculation logic where appropriate.

---

## 6.4 Local Model Fingerprints

Mutable local model definitions used in research require identity even before formal versioning.

Store:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

This applies to:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

Released definitions use formal version identity.

---

# 7. Research and Strategy Execution Boundaries

## 7.1 Signal Research Scopes

Signal Research supports three explicit scopes:

```text
Market Model only
Signal Model only
Market Model × Signal Model
```

A research definition must state which scope is being evaluated.

Single analytical events should normally be studied through one-condition Market or Signal Models rather than by bypassing model contracts.

---

## 7.2 Strategy Research

Strategy Research evaluates complete Strategy Models.

It owns:

- batch or vectorized backtesting,
- trade simulation datasets,
- execution assumptions,
- reusable Strategy Research Datasets,
- walk-forward analysis,
- Monte Carlo analysis,
- robustness analytics.

---

## 7.3 Strategy Execution Modes

Strategy Execution may support:

```text
Replay Execution
Paper Execution
Live Execution
```

Replay Execution uses:

- published historical data,
- Replay Clock,
- runtime-style order, fill and position semantics.

Paper Execution uses:

- live market data,
- simulated broker interaction.

Live Execution uses:

- live market data,
- real broker interaction.

These modes are distinct from batch or vectorized Research backtesting.

---

# 8. Event System

## 8.1 Purpose

The Event System decouples components where asynchronous or reactive communication provides real value.

The architecture is hybrid:

```text
Direct Calls for deterministic Research
Events for Strategy Execution where justified
```

The framework does not use event-driven architecture everywhere.

---

## 8.2 Events and Commands

Events represent facts that occurred.

Examples:

```text
MarketBarReceived
SignalGenerated
OrderSubmitted
OrderFilled
PositionUpdated
```

Commands represent requested actions.

Examples:

```text
SubmitOrder
CancelOrder
ClosePosition
```

Events and commands must not be confused.

---

## 8.3 Research Usage

Research uses direct calls and explicit orchestration by default.

Events may support:

- progress reporting,
- audit logging,
- monitoring,
- result persistence.

Events must not define the computational semantics of Research.

---

## 8.4 Strategy Execution Usage

Strategy Execution may use an EventBus for:

- provider input,
- analytical updates,
- SignalOccurrence publication,
- order lifecycle,
- broker events,
- monitoring,
- retry boundaries.

Critical state transitions must remain explicit.

---

## 8.5 Event Model

Events are immutable.

Conceptual example:

```python
@dataclass(frozen=True, slots=True)
class Event:
    event_id: UUID
    occurred_at: datetime
    correlation_id: UUID | None
```

Provider SDK objects must not be published directly.

---

## 8.6 Event Bus

Conceptual contract:

```python
class EventBus(Protocol):
    def publish(self, event: Event) -> None:
        ...

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> Subscription:
        ...
```

Possible implementations:

```text
InMemoryEventBus
AsyncEventBus
RedisEventBus
```

Version 1 begins with an in-memory implementation unless a demonstrated requirement justifies more.

---

## 8.7 Event System Rules

1. Research uses direct calls by default.
2. Strategy Execution may use events where justified.
3. Events represent facts.
4. Commands represent requested actions.
5. Events are immutable.
6. Provider and broker objects do not cross boundaries.
7. Handlers are focused and testable.
8. Execution event handling is idempotent where required.
9. Critical events are not silently dropped.
10. Distributed messaging is deferred.

---

# 9. Configuration Architecture

## 9.1 Purpose

Configuration defines how framework components are selected, instantiated and composed.

Configuration remains separate from implementation.

Supported configuration areas include:

- system,
- market data,
- Market Analysis,
- model definitions,
- research,
- Strategy Execution.

---

## 9.2 Configuration Principles

Configuration must be:

- explicit,
- validated,
- versionable,
- serializable,
- reproducible,
- environment-independent where possible.

Arbitrary executable Python code is forbidden in configuration files.

---

## 9.3 Configuration Technology

Pydantic is preferred for:

- configuration models,
- external DTOs,
- validation boundaries,
- serialization schemas.

Pydantic is not the automatic implementation of every domain object.

---

## 9.4 Configuration Layers

Suggested precedence:

```text
Framework Defaults
        ↓
Environment Configuration
        ↓
User Configuration
        ↓
Run-Specific Overrides
```

Resolved configuration is persisted with each run.

---

## 9.5 Market Analysis Configuration

A Market Analysis component configuration selects:

```text
component type
component id
parameters
timeframe semantics
alignment policy
cache policy where configurable
```

Example:

```yaml
market_analysis:
  atr_14_1h:
    component: atr
    parameters:
      period: 14
    computation_timeframe: 1h
    evaluation_timeframe: 1m
    alignment_policy: LAST_CLOSED_BAR
```

Dependencies should normally be declared by the component contract.

Configuration may select aliases and parameter values.

---

## 9.6 Model Configuration

Market and Signal Model configuration uses explicit expression trees.

Example:

```yaml
signal_model:
  id: bullish_sweep
  version: 1

  expression:
    operator: AND
    children:
      - component: liquidity_sweep
        timeframe: 1m
        condition:
          field: direction
          equals: bullish

      - component: price_reclaim
        timeframe: 1m
        condition:
          equals: true
```

Model configuration must not embed arbitrary executable logic.

---

## 9.7 Research Configuration

Research configuration defines a bounded research space.

It must distinguish:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

It must not interpret every list as a logical OR or unrestricted Cartesian product.

Signal Research configuration must explicitly declare one of:

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

---

## 9.8 Strategy Configuration

A Strategy Model configuration selects:

```text
Market Model
Signal Model
Exit Model
Risk Model
```

Position sizing is configured through the Risk Model in Version 1.

---

## 9.9 Strategy Execution Configuration

Defines:

- execution mode,
- broker,
- account,
- instrument mapping,
- strategy selection,
- order policy,
- operational limits,
- reconnect policy,
- execution risk controls.

Secrets are loaded from environment variables or external secret storage.

---

## 9.10 Configuration Versioning

Every persisted run records:

```text
resolved configuration
configuration schema version
component versions or fingerprints
model versions or fingerprints
dataset versions
framework version
```

A material change creates a new run identity.

---

# 10. Module Structure

## 10.1 High-Level Layout

```text
trading-research-framework/
├── src/trading_framework/   # modular monolith (ADR-0001)
├── apps/                    # deployable consumers (e.g. apps/dashboard)
├── scripts/                 # thin CLIs over application use cases
├── deploy/                  # containers / infra-as-code / local AWS runbook
├── tests/                   # framework tests
├── docs/                    # vision, reference, planning, adr, agents, onboarding
├── demo/output/             # generated demo artifacts (not source-of-truth docs)
├── user_data/               # user-owned content (ADR-0002; gitignored)
├── pyproject.toml           # root package + uv workspace root
└── README.md
```

Binding layout rules: **ADR-0022**. Apps must not import research/execution
engines or provider/importer adapters. Dashboard deploy stays co-located under
`apps/dashboard/deploy/`.

---

## 10.2 Source Package

```text
src/
└── trading_framework/
    ├── core/
    ├── time/
    ├── market/
    ├── market_analysis/
    ├── strategy/
    ├── research/
    ├── execution/
    ├── events/
    ├── config/
    ├── infrastructure/
    ├── application/
    └── api/
```

---

## 10.3 Core Module

```text
src/trading_framework/core/
├── types/
├── enums/
├── identifiers/
├── protocols/
├── exceptions/
└── result/
```

The Core module contains only stable shared primitives.

It must not become a generic utilities dumping ground.

---

## 10.4 Time Module

```text
src/trading_framework/time/
├── models/
├── calendars/
├── sessions/
├── clocks/
├── rolls/
└── protocols.py
```

---

## 10.5 Market Module

```text
src/trading_framework/market/
├── models/
├── datasets/
├── requests/
├── providers/
├── importers/
├── normalization/
├── validation/
├── repositories/
└── services/
```

Concrete providers and storage implementations belong to Infrastructure.

---

## 10.6 Market Analysis Module

Initial minimal structure:

```text
src/trading_framework/market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Possible later structure:

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

The conceptual taxonomy is stable even if the folder hierarchy evolves.

---

## 10.7 Strategy Module

```text
src/trading_framework/strategy/
├── signal_models/
├── market_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
├── occurrences/
├── models/
└── protocols.py
```

The module contains:

- contracts,
- neutral generic implementations,
- expression evaluation,
- Strategy Domain value objects.

Proprietary compositions belong to `user_data/`.

---

## 10.8 Research Module

```text
src/trading_framework/research/
├── signal_research/
├── strategy_research/
├── datasets/
├── simulation/
├── analytics/
├── insights/
├── families/
├── validation/
└── protocols.py
```

Batch and vectorized backtesting belong under Research.

---

## 10.9 Execution Module

```text
src/trading_framework/execution/
├── models/
├── brokers/
├── orders/
├── fills/
├── positions/
├── risk_controls/
├── reconciliation/
├── replay/
├── paper/
├── live/
└── services/
```

Concrete broker adapters belong to Infrastructure.

---

## 10.10 Events Module

```text
src/trading_framework/events/
├── models/
├── bus/
├── handlers/
├── commands/
└── protocols.py
```

Domain-specific events may live near their owning domain where clearer.

---

## 10.11 Configuration Module

```text
src/trading_framework/config/
├── models/
├── loaders/
├── defaults/
├── validation/
└── resolution/
```

---

## 10.12 Infrastructure Module

```text
src/trading_framework/infrastructure/
├── providers/
│   ├── databento/
│   ├── binance/
│   ├── rithmic/
│   └── mt5/
├── importers/
├── brokers/
├── storage/
│   ├── parquet/
│   ├── duckdb/
│   └── postgres/
├── cache/
├── messaging/
└── observability/
```

Infrastructure depends on framework contracts.

Domain modules do not depend on infrastructure implementations.

---

## 10.13 Application Module

```text
src/trading_framework/application/
├── market_data/
├── signal_research/
├── strategy_research/
├── strategy_execution/
└── services/
```

Responsibilities:

- use-case orchestration,
- component loading,
- transaction boundaries,
- workflow entry points.

Application code coordinates domains.

It does not contain reusable domain algorithms.

---

## 10.14 API Module

```text
src/trading_framework/api/
├── rest/
├── websocket/
├── schemas/
└── dependencies/
```

The API layer must not contain business logic.

FastAPI may be one adapter, but the domain does not depend on FastAPI.

---

# 11. User Data Structure

## 11.1 Purpose

`user_data/` contains user-owned assets and proprietary know-how.

Suggested structure:

```text
user_data/
├── config/
├── data/
├── development/
├── candidates/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategies/
├── research/
├── analytics/
├── reports/
├── notebooks/
├── tests/
└── secrets/
```

---

## 11.2 Working Components

```text
user_data/development/market_analysis/
```

Contains unstable local components under active development.

These may change freely.

Research use requires implementation fingerprints.

---

## 11.3 Candidate Components

```text
user_data/candidates/market_analysis/
```

Contains stable candidates being prepared for possible promotion into `src/`.

---

## 11.4 Proprietary Model Definitions

```text
user_data/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
└── strategies/
```

Contains proprietary model definitions and compositions.

Mutable definitions used in research require fingerprints.

---

## 11.5 Research Results

```text
user_data/research/
├── signal_research/
├── strategy_research/
├── datasets/
├── runs/
└── metadata/
```

Signal Research and Strategy Research results remain separate.

---

## 11.6 Analytics

```text
user_data/analytics/
├── insights/
├── rankings/
├── families/
├── correlations/
├── clusters/
└── robustness/
```

Analytics may be regenerated without recomputing unchanged research datasets.

---

## 11.7 Reports and Notebooks

```text
user_data/reports/
user_data/notebooks/
```

Notebooks are exploratory.

Reusable logic should move into either:

```text
src/trading_framework/
```

or:

```text
user_data/development/
user_data/candidates/
user_data/*_models/
```

---

## 11.8 Secrets

```text
user_data/secrets/
```

This directory is not committed.

Environment variables or external secret storage are preferred.

---

# 12. Tests Structure

Suggested structure:

```text
tests/
├── unit/
│   ├── core/
│   ├── time/
│   ├── market/
│   ├── market_analysis/
│   ├── strategy/
│   ├── research/
│   ├── execution/
│   └── events/
├── integration/
│   ├── providers/
│   ├── importers/
│   ├── brokers/
│   ├── storage/
│   └── messaging/
├── end_to_end/
└── fixtures/
```

User-owned components may have tests under:

```text
user_data/tests/
```

Required test areas include:

- dataset lifecycle,
- component identity,
- dependency graph,
- cache identity,
- multitimeframe alignment,
- `available_at`,
- MarketFieldReference,
- Market Model expression evaluation,
- Signal Model expression evaluation,
- SignalOccurrence semantics,
- Research workflow scope,
- backtest/replay separation.

Unit tests must not require live external systems.

Integration tests are opt-in when external systems are required.

---

# 13. Final Technical Architecture Rules

1. UTC is used internally.
2. Naive datetimes are forbidden.
3. Provider schemas are normalized at boundaries.
4. Market data is accessed through contracts.
5. Historical data uses Parquet by default.
6. Dataset identity and lifecycle are explicit.
7. Finalization and publication are separate.
8. Research consumes published DatasetRefs.
9. Research does not trigger hidden downloads or mutation.
10. The analytical domain is named Market Analysis.
11. Market Analysis outputs are Features, Structures and States.
12. Detector and Classifier are implementation patterns.
13. The shared runtime is named Market Analysis Engine.
14. Dependencies are explicit and DAG-based.
15. Equivalent deterministic nodes are calculated once.
16. Cache identity includes source, computation and evaluation timeframe.
17. Resampling is explicit and reusable.
18. Higher-timeframe alignment uses legal `available_at` semantics.
19. Market and Signal Models are declarative compositions.
20. Models do not access arbitrary DataFrames.
21. Controlled MarketFieldReferences are allowed.
22. SignalOccurrence belongs to the Strategy Domain.
23. Position sizing belongs to the Risk Model in Version 1.
24. Batch/vectorized backtesting belongs to Research.
25. Replay, Paper and Live modes belong to Strategy Execution.
26. Working components and models used in research require fingerprints.
27. Framework code lives in `src/`.
28. Proprietary know-how lives in `user_data/`.
29. `src/` never imports concrete user components directly.
30. Infrastructure depends on framework contracts.
31. Domain logic does not depend on infrastructure.
32. Signal Research, Strategy Research and Strategy Execution remain independent.
33. Stored research datasets are reusable.
34. Technical complexity is introduced only when justified.
