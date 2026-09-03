# Trading Research Framework

# ARCHITECTURE_TECHNICAL.md

> **Sprint 054 T004 note:** most of this document's sections were classified
> CURRENT (already built, verified against `src/trading_framework/`) by
> `docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
> and have moved to
> [`docs/reference/system/ARCHITECTURE_TECHNICAL.md`](../reference/system/ARCHITECTURE_TECHNICAL.md).
> What remains here is future-facing, ambiguous-status, or a section whose
> "suggested" content has diverged structurally from the actual codebase
> (notably the Module Structure and User Data Structure sections — the
> authoritative as-built layout is
> [`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md)). See the
> classification doc for the full section-by-section reasoning and evidence
> before assuming anything below is or is not built.

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

## 2.4 Trading Sessions

*(Classified MIXED by T002 — as-built status is nuanced, see
`SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §2.4. A session
protocol/contract exists (`time/sessions/protocol.py`), but only one
concrete session resolver is implemented (CME ES RTH); the other named
sessions below have no matching implementation.)*

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

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §2.5. No
dedicated `Calendar` class or `time/calendars/` directory was found; the
one session resolver that exists is timezone/session-boundary focused, not
a separate generic calendar abstraction.)*

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

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §2.6. No
dedicated holiday-rule module or `holiday_policy` field was located.)*

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

## 2.10 Time Model Rules (see also the current-behavior portion in `docs/reference/system/ARCHITECTURE_TECHNICAL.md`)

*(This numbered rule list also appears, unchanged, in the reference copy —
duplicated here only as the anchor for the calendar/holiday/session caveats
above. Do not treat this as a second independent version of the rules.)*

---

# 3. Market Data Architecture

## 3.3 Provider and Importer Contracts

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §3.3. The
underlying capability (provider/importer separation) is CURRENT via
`market/importers/` and `infrastructure/providers/`; the specific named
contract protocols below were not found under these names.)*

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

## 3.5 Instrument Mapping

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §3.5. No
dedicated instrument-mapping module or config schema was located.)*

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

## 3.7 Missing Data

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §3.7. The
named policy enum below was not located verbatim; gap-detection tests exist
in spirit.)*

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

## 3.9 Storage Layers

*(Classified MIXED by T002 — the actual, documented canonical layout is
`user_data/market_data/{raw,metadata,normalized,continuous}/` per
[`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md) §11, a
different and narrower set of directory names than the suggestion below.
The concept — raw vs. normalized vs. derived data — is realized; the exact
directory names are not.)*

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

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §3.10. The
specific defaults table below was not verified against actual
partition-writer code.)*

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

## 3.15 Live Ingestion

*(Classified FUTURE by T002. `execution/modes.py` supports only
`ExecutionMode.DRY_RUN`; the live-runtime consumer side of this pipeline is
not built end-to-end.)*

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

*(Classified FUTURE by T002. `execution/modes.py` supports only
`ExecutionMode.DRY_RUN`; no `ReplayClock` implementation exists. Batch
backtesting, the other half of this section's contrast, is independently
CURRENT via `research/simulation/` and documented in
`docs/reference/system/ARCHITECTURE_TECHNICAL.md`.)*

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

# 4. Market Analysis Architecture

## 4.4 State

*(Classified MIXED by T002 — as-built status is nuanced, see
`SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §4.4. Features
and Structures are clearly built; no distinct "State" output type or
`states/` directory was found beyond a single generically-named
`volatility.state` component. The State leg of the Feature/Structure/State
taxonomy is the least built of the three.)*

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

# 5. Market Analysis Engine

## 5.9 Intrabar Components

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §5.9. No
dedicated "intrabar" contract or module was located.)*

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

## 5.12 Local Development and Promotion

*(Classified FUTURE by T002. `Grep` for `reproducibility_status`/
`EXPERIMENTAL` across `src/trading_framework/` returned zero matches; the
actual `user_data/` canonical layout has no `development/` or `candidates/`
directories.)*

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

# 6. Model Composition Architecture

## 6.4 Local Model Fingerprints

*(Classified FUTURE by T002 — the model-layer counterpart of §5.12's
unbuilt promotion/fingerprint lifecycle. Same
`reproducibility_status`/`EXPERIMENTAL` search returned zero matches.)*

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

## 7.3 Strategy Execution Modes

*(Classified FUTURE by T002. `execution/modes.py`:
`SUPPORTED_EXECUTION_MODES = frozenset({ExecutionMode.DRY_RUN})` — only
`DRY_RUN` is supported "in the current increment". `execution/broker_sim/`
exists but the three named runtime modes are not available end-to-end.)*

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

*(Classified FUTURE by T002 in full — the single largest fully-unbuilt
block found across T001–T003. `src/trading_framework/events/__init__.py`
contains only a one-line docstring; no `Event`, `EventBus`, handler, or
command implementation exists anywhere in `src/trading_framework/`. See
`SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §8 for the full
evidence, including the negative-result greps for every named type below.)*

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

*(Classified MIXED by T002. "Explicit" and "validated" are confirmed via
Pydantic-backed config (`config/loader.py`); "versionable"/"reproducible"
in the sense of persisted resolved-configuration-per-run was not found as a
general framework capability — see §9.10 below.)*

Configuration must be:

- explicit,
- validated,
- versionable,
- serializable,
- reproducible,
- environment-independent where possible.

Arbitrary executable Python code is forbidden in configuration files.

---

## 9.4 Configuration Layers

*(Classified FUTURE by T002. `config/loader.py` implements a single-file
TOML loader with no layered precedence/merge logic; no
environment-variable overlay or run-override merge step was found.)*

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

## 9.6 Model Configuration

*(Classified MIXED by T002. `model_expression/` and `model_authoring/`
implement expression-tree-based model definitions, consistent with "no
arbitrary executable logic"; a literal YAML-file model-config loader
matching this exact example schema was not independently located.)*

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

## 9.9 Strategy Execution Configuration

*(Classified AMBIGUOUS by T002 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §9.9.
`execution/safety.py` and `execution/repositories/` plausibly implement
part of this, but since only `DRY_RUN` execution mode is supported (§7.3),
most of the broker/account/reconnect-policy configuration below has no
live counterpart to configure yet.)*

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

*(Classified FUTURE by T002 at the general-rule level. Dataset-level and
predictive-run-level fingerprinting is confirmed CURRENT elsewhere (e.g.
Predictive Research's dataset/run envelopes), but a generic, framework-wide
"every persisted run records resolved configuration + framework version"
guarantee applying uniformly across all workflows was not found.)*

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

*(§10.1 High-Level Layout and §10.13 Application Module were classified
CURRENT and moved to
[`docs/reference/system/ARCHITECTURE_TECHNICAL.md`](../reference/system/ARCHITECTURE_TECHNICAL.md#module-structure).
The remaining subsections below are written as suggestions — "Initial
minimal structure", "Possible later structure" — and the actual
`src/trading_framework/` layout has diverged from them in a consistent,
structural way. They are left here as historical/illustrative context, not
an as-built description. The authoritative current package tree is
[`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md). See
`SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §10 for the
full per-subsection diff.)*

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

*(Classified FUTURE by T002. `events/` contains only `__init__.py` with a
one-line docstring; none of the subdirectories below exist. Same finding as
§8.)*

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

## 10.14 API Module

*(Classified FUTURE by T002. No `src/trading_framework/api/` package
exists at all. `apps/dashboard/` and `apps/cli/` are the actual current-day
consumer surfaces, neither of which is the REST/WebSocket API described
below.)*

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

*(Classified MIXED/FUTURE/AMBIGUOUS by T002 across every subsection — the
actual, documented canonical `user_data/` layout is
[`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md) §11:
`user_data/{market_data,research,runtime,reports,config,components,models}/`,
a materially flatter structure than every proposal below. Left here in
full as historical/illustrative context rather than split subsection by
subsection — see
`SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md` §11 for the
per-subsection diff.)*

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
