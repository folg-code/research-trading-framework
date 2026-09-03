# Architecture Technical — As-Built Reference

> Moved from `docs/vision/ARCHITECTURE_TECHNICAL.md` by Sprint 054 T004
> (vision reclassification and reference layering). The sections below were
> classified **CURRENT** (or are the current-behavior portion of a section
> classified **MIXED**) against the codebase as of 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references. Content is reproduced verbatim from the vision document — this
> move does not rewrite any architectural decision.
>
> The Event System (§8 of the source document), the suggested Module
> Structure (§10.2–§10.12, §10.14 — the actual layout lives in
> [`docs/reference/system/MODULE_MAP.md`](MODULE_MAP.md)), the User Data
> Structure (§11 — actual layout also in `MODULE_MAP.md` §11), and several
> other future-facing or ambiguous-status sections remain in
> [`docs/vision/ARCHITECTURE_TECHNICAL.md`](../../vision/ARCHITECTURE_TECHNICAL.md).

---

## Time Model

### Timestamp Policy

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

### Timezone Policy

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

### Futures Contract Rolls

> As-built note: the Contract-vs-Continuous-Dataset distinction and the roll
> workflow are implemented (`application/market_data/build_roll_schedule.py`,
> `application/market_data/derive_continuous_ohlcv.py`,
> `infrastructure/storage/{roll_schedule_manifest_store,roll_schedule_repository,continuous_manifest_store}.py`).
> The exact named metadata fields below were not individually diffed against
> the roll schedule schema — field-level parity is unverified.

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

### Clock Abstraction

> As-built note: the `Clock` protocol and `SystemClock`/`FixedClock` are
> implemented (`time/clocks/{protocol,system,fixed}.py`,
> `tests/unit/test_clocks.py`). `ResearchClock` and `ReplayClock` have no
> matching implementation, consistent with Replay Execution itself being
> unbuilt (see `docs/vision/ARCHITECTURE_TECHNICAL.md` §3.16/§7.3).

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

### Observed Time and Available Time

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

### Time Model Rules

> As-built note: rules 1–3, 6, 9–12 below are CURRENT. Rules touching
> calendars/holidays (5) and full Clock coverage (8) inherit the
> MIXED/AMBIGUOUS status of the Trading Calendars, Holidays, and Clock
> Abstraction sections that remain in
> `docs/vision/ARCHITECTURE_TECHNICAL.md`.

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

## Market Data Architecture

### Purpose

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

### Supported Data Sources

> As-built note: `infrastructure/providers/binance/` and
> `infrastructure/importers/{csv,databento}/` are implemented. Rithmic and
> MetaTrader 5 are named below but have no matching provider package.

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

### Data Normalization

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

### Data Validation

Validation categories include:

#### Schema Validation

- required fields,
- types,
- nullability,
- ranges,
- precision.

#### Temporal Validation

- timestamp ordering,
- duplicates,
- gaps,
- timezone correctness,
- session consistency.

#### Market Validation

- OHLC invariants,
- non-negative volume,
- valid bid/ask relationship,
- valid instrument identity.

#### Dataset Validation

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

### Historical Storage

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

### Dataset Identity

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

### Dataset Lifecycle

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

#### FINALIZED

The dataset or partition has been:

- ordered,
- deduplicated,
- validated,
- checksummed,
- closed for normal writes.

#### PUBLISHED

The dataset version is stable and available for Research or Replay Execution.

A combined workflow such as:

```text
finalize_and_publish()
```

may exist, but it must record both transitions explicitly.

A published dataset version is immutable.

---

### Dataset Access

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

### Research Data Rule

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

### Market Data Architecture Rules

> As-built note: rules 1–10, 12–14 below are CURRENT/MIXED and are covered
> above. Rule 15 ("Live storage does not block runtime processing")
> presupposes the live-ingestion pipeline described in
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §3.15, which remains FUTURE.

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

## Market Analysis Architecture

### Purpose

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

### Feature

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

### Structure

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

### Detectors, Classifiers and Transformations

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

### Component Contract

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

### Component Request

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

### MarketFieldReference

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

---

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

---

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

---

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

---

### Lazy Execution

> As-built note: the dependency-planning architecture (`market_analysis/planning/`)
> structurally supports lazy resolution; an execution-time proof that
> unrelated components are skipped (rather than eagerly computed and
> discarded) was not independently traced.

The engine calculates only requested outputs and their transitive dependencies.

Unrelated components are not calculated.

Lazy execution is mandatory for large research spaces.

---

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

---

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

---

### Temporal Alignment

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

### Output Forms

> As-built note: Feature and Structure output forms are confirmed. State
> output forms inherit the caveat noted in
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §4.4 (the State category is the
> least built of the three).

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

---

### Market Analysis Engine Rules

> As-built note: rule 12 ("Working components used in research require
> fingerprints") inherits the FUTURE status of
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §5.12 "Local Development and
> Promotion" — the fingerprint fields it requires do not exist in `src/`.

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

## Model Composition Architecture

### Market Model

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

### Signal Model

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

### Strategy Model

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

## Research and Strategy Execution Boundaries

### Signal Research Scopes

Signal Research supports three explicit scopes:

```text
Market Model only
Signal Model only
Market Model × Signal Model
```

A research definition must state which scope is being evaluated.

Single analytical events should normally be studied through one-condition Market or Signal Models rather than by bypassing model contracts.

---

### Strategy Research

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

## Configuration Architecture

### Configuration Technology

Pydantic is preferred for:

- configuration models,
- external DTOs,
- validation boundaries,
- serialization schemas.

Pydantic is not the automatic implementation of every domain object.

---

### Market Analysis Configuration

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

### Research Configuration

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

### Strategy Configuration

A Strategy Model configuration selects:

```text
Market Model
Signal Model
Exit Model
Risk Model
```

Position sizing is configured through the Risk Model in Version 1.

---

## Module Structure

### High-Level Layout

```text
trading-research-framework/
├── src/trading_framework/   # modular monolith (ADR-0001)
├── apps/                    # deployable consumers (e.g. apps/dashboard)
├── scripts/                 # thin CLIs over application use cases
├── deploy/                  # containers / infra-as-code / local AWS runbook
├── tests/                   # framework tests
├── docs/                    # vision, reference, planning, adr, agents, onboarding
├── artifacts/demo/          # generated demo HTML (not source-of-truth docs)
├── scratch/                 # local-only logs/probes (gitignored)
├── user_data/               # user-owned content (ADR-0002; gitignored)
├── pyproject.toml           # root package + uv workspace root
└── README.md
```

Binding layout rules: **ADR-0022**. Apps must not import research/execution
engines or provider/importer adapters. Dashboard deploy stays co-located under
`apps/dashboard/deploy/`. Prefer `scratch/` for ephemeral logs (not root `.tmp_*`).

---

### Application Module

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

> As-built note: the actual package set matches `market_data`,
> `signal_research`, `strategy_research` directly (`strategy_execution` is
> named `execution/` in code); see
> [`docs/reference/system/MODULE_MAP.md`](MODULE_MAP.md) for the current,
> authoritative package tree, which has several additional
> workflow-orchestration packages not listed above
> (`market_analysis/`, `model_evaluation/`, `predictive_research/`,
> `robustness_research/`).

---

## Tests Structure

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

> As-built note: the actual `tests/` tree is a close match to the pattern
> above (unit tests mirror module ownership, integration tests are opt-in,
> `tests/e2e/` — named `e2e`, not `end_to_end`). `tests/unit/events` and
> `tests/integration/{brokers,messaging}` do not exist, consistent with the
> Event System and live-broker integration being unbuilt.

---

## Final Technical Architecture Rules

> As-built note: this is a compilation restating the whole document. The
> large majority of these rules map to CURRENT/MIXED sub-claims covered
> above. Rule 25 ("Replay, Paper and Live modes belong to Strategy
> Execution") and rule 26 (fingerprints for working components/models)
> inherit the FUTURE findings in
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §7.3, §5.12 and §6.4.

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
