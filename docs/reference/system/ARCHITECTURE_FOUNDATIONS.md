# Architecture Foundations — As-Built Reference

> Moved from `docs/vision/ARCHITECTURE_FOUNDATIONS.md` by Sprint 054 T004
> (vision reclassification and reference layering). The sections below were
> classified **CURRENT** (or are the current-behavior portion of a section
> that was classified **MIXED**) against the codebase as of 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references. Content is reproduced verbatim from the vision document — this
> move does not rewrite any architectural decision.
>
> Future-facing, ambiguous-status, and not-yet-built content (the promotion
> lifecycle in former §4.12, the "Composition Over Inheritance" style rule in
> former §5.5, and the Replay/Live Execution runtime modes in former §6.5)
> remains in
> [`docs/vision/ARCHITECTURE_FOUNDATIONS.md`](../../vision/ARCHITECTURE_FOUNDATIONS.md).

---

## System Capabilities

The framework supports three independent primary capabilities:

```text
Signal Research
Strategy Research
Strategy Execution
```

These capabilities share reusable domains, contracts and component definitions.

They are not stages of one mandatory pipeline.

Incorrect:

```text
Signal Research
        ↓
Strategy Research
        ↓
Strategy Execution
```

Correct:

```text
                       Shared Definitions
          Market Analysis / Models / Time / Data
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
      Signal Research   Strategy Research   Strategy Execution
```

Rules:

1. Signal Research must be usable without Strategy Research.
2. Strategy Research must be usable without a previous Signal Research run.
3. Strategy Execution must not depend on research datasets, rankings, reports or analytics.
4. Shared deterministic artifacts may be reused through explicit contracts.
5. Reuse does not create a mandatory workflow dependency.
6. Research never forms one runtime pipeline with execution.

---

## Core Philosophy

### Market Facts Before Interpretation

The Market Domain represents provider-independent market facts and trusted market datasets.

Examples:

- instruments,
- bars,
- trades,
- quotes,
- order-book updates,
- market dataset metadata.

The Market Domain does not interpret market behaviour.

It does not define:

- trend,
- volatility regime,
- liquidity structures,
- signals,
- exits,
- risk models,
- strategies,
- research conclusions.

Interpretation belongs to higher-level analytical and model-definition domains.

---

### Market Analysis as a Reusable Language

The analytical domain is named:

```text
Market Analysis
```

The previous name `Technical Analysis` is rejected as too narrow because the domain may include:

- classical indicators,
- statistical features,
- market structures,
- session analysis,
- liquidity analysis,
- order flow,
- market microstructure,
- options-derived context,
- event detection,
- state classification,
- multitimeframe analysis.

The Market Analysis Domain owns reusable, strategy-independent calculations, detections and classifications derived from market-related data.

Its minimal semantic taxonomy is:

```text
Market Analysis Components
├── Features
├── Structures
└── States
```

#### Features

Features represent measurable or time-aligned analytical properties.

Examples:

- ATR,
- VWAP,
- slope,
- rolling volatility,
- wick ratio,
- distance to a level,
- volume delta.

#### Structures

Structures represent identified market objects, levels, patterns or events.

Examples:

- Pivot,
- Swing High,
- Higher High,
- Lower Low,
- Session Range,
- Liquidity Level,
- Liquidity Sweep,
- Fair Value Gap,
- Break of Structure.

#### States

States represent classifications of the market at a given time.

Examples:

- trend = bullish,
- market regime = ranging,
- volatility = expanding,
- structure = continuation,
- liquidity = compressed.

`Detector`, `Classifier` and `Transformation` are implementation patterns, not top-level domain categories.

Examples:

```text
PivotDetector
    → Pivot Structure

LiquiditySweepDetector
    → LiquiditySweep Structure

TrendClassifier
    → Trend State
```

Market Analysis does not decide whether a trade should be entered, exited or sized.

---

### Models as Declarative Compositions

Market Models and Signal Models consume the same reusable Market Analysis layer.

The framework does not create separate:

```text
Market Features / Market States
Signal Features / Signal States
```

The role of an analytical output is determined by the model composition that consumes it.

#### Market Model

A Market Model is a named, versioned and declarative composition defining a market context.

```text
Market Model
=
expression over Market Analysis outputs
```

Example:

```text
Bullish Expansion Market Model
=
trend_state_4h == bullish
AND
volatility_state_1h == expanding
AND
price_above_vwap_15m == true
```

A Market Model does not calculate its dependencies internally.

#### Signal Model

A Signal Model is a named, versioned and declarative composition defining a trading opportunity.

```text
Signal Model
=
expression over Market Analysis outputs
```

Example:

```text
Bullish Sweep Signal Model
=
liquidity_sweep_1m.direction == bullish
AND
price_reclaim_1m == true
AND
wick_ratio_1m >= 0.6
```

A Signal Model is not a standalone detector and does not own hidden analytical calculations.

#### Semantic Difference

```text
Market Model:
Which analytical conditions define the market context?

Signal Model:
Which analytical events and conditions define a trading opportunity?
```

Both may reference the same analytical component.

Model expressions must not access arbitrary raw DataFrames or storage objects directly.

A simple source-data condition must use either:

```text
an explicit Market Analysis Feature
```

or:

```text
a controlled MarketFieldReference
```

A `MarketFieldReference` must preserve:

- dataset lineage,
- field identity,
- timeframe,
- temporal availability semantics,
- compatibility with the dependency graph.

This keeps simple research expressions possible without bypassing the architecture.

---

### Strategy as Composition

A complete Strategy Model is composed from independent model definitions:

```text
Strategy Model
=
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

The Strategy Model is a composition definition, not a god object.

It must not own one monolithic implementation containing:

```text
calculate indicators
detect entries
calculate exits
size positions
submit orders
```

Each component must remain independently:

- identifiable,
- testable,
- reusable,
- replaceable,
- versionable once published.

Position sizing belongs to the Risk Model in Version 1.

A separate Position Sizing Model may be introduced only when demonstrated research or execution requirements justify independent composition and versioning.

---

### Development, Composition and Research Are Different Activities

The framework distinguishes three kinds of work.

#### Analytical Component Development

Purpose:

```text
Develop reusable tools for describing market behaviour.
```

Outputs:

- Features,
- Structures,
- States,
- analytical contracts,
- tests,
- reusable execution infrastructure.

This is framework or library development.

#### Model Development

Purpose:

```text
Compose analytical outputs into explicit trading hypotheses.
```

Outputs:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

This defines what a model means.

It is not yet research.

#### Model Research

Purpose:

```text
Evaluate model behaviour on explicit datasets and assumptions.
```

Outputs:

- Signal Research Datasets,
- Strategy Research Datasets,
- analytics,
- reports,
- rankings,
- robustness evidence.

A model definition must remain separate from the workflow that researches or executes it.

---

### Research Computation and Analytics Are Separate

Research computation creates reusable factual result datasets.

Research analytics interprets those stored results.

```text
Research Configuration
        ↓
Dependency Resolution
        ↓
Computation
        ↓
Persistent Research Dataset
        ↓
Independent Analytics
```

New filtering, ranking, reporting or family analysis must not automatically trigger recomputation of unchanged source results.

Expensive deterministic intermediate results should be persisted when reuse provides meaningful value.

---

### Market Analysis Engine

The shared analytical execution capability is named:

```text
Market Analysis Engine
```

It may contain:

```text
Component Registry
Dependency Graph
Component Executor
Component Cache
Temporal Alignment
```

The engine calculates Features, Structures and States.

It does not own Market Models, Signal Models or Strategy Models.

---

### Dependency-First Computation

The framework must not recalculate the same deterministic dependency independently for every experiment.

The computational model is:

```text
Requested Models and Research Space
                ↓
       Shared Dependency Graph
                ↓
          Execution Plan
                ↓
       Reusable Component Results
```

The dependency system must:

- expose dependencies before execution,
- remain acyclic,
- deduplicate equivalent nodes,
- calculate only requested outputs and transitive dependencies,
- include all material inputs in cache identity.

Hidden calls to other analytical components are prohibited.

---

### Multitimeframe Is a Property of Analytical Requests

Multitimeframe is not a special Strategy Model or Market Model type.

A Market Analysis component request may specify a computation timeframe.

The architecture must distinguish:

```text
source timeframe
computation timeframe
evaluation timeframe
```

Resampling is an explicit shared dependency or derived dataset transformation.

The default higher-timeframe alignment policy is:

```text
LAST_CLOSED_BAR
```

A result must not be available before the information required to calculate it was known.

Temporal outputs must preserve or allow derivation of:

```text
observed_at
available_at
```

Incomplete higher-timeframe values may be used only through an explicit intrabar contract.

---

### Research Spaces Must Be Bounded and Observable (current-behavior portion)

> This subsection was classified MIXED by T001. The framework-level
> distinction below (fixed selection / independent alternatives / bounded
> search space) and the progressive-research staircase are realized today
> through Robustness Research's bounded experiment/variant model. The
> planner-observability metadata (candidate count, applied constraints,
> estimated output size) named later in the vision section has **no code
> counterpart** and remains in
> `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §4.10.

The framework must distinguish:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

A list does not automatically mean:

- logical `OR`,
- full Cartesian expansion.

The framework should support progressive research:

```text
individual analytical components
        ↓
pairwise interactions
        ↓
small Market and Signal Model compositions
        ↓
complete Strategy Models
        ↓
robustness validation
```

---

### Local Ownership of Know-How

Reusable framework implementation belongs in:

```text
src/
```

Private user assets and proprietary know-how belong in:

```text
user_data/
```

The public framework may contain:

- Market Data contracts,
- Market Analysis components,
- dependency and execution engines,
- time abstractions,
- generic model-composition contracts,
- research infrastructure,
- execution infrastructure.

Private user space normally contains:

- Market Model definitions,
- Signal Model definitions,
- Exit Model definitions,
- Risk Model definitions,
- Strategy Model definitions,
- research configurations,
- parameter selections,
- local market data,
- research datasets,
- rankings,
- reports,
- notebooks,
- proprietary hypotheses.

The framework provides the reusable language.

Private user space defines how that language is composed into trading know-how.

---

### Trusted and Reproducible Market Data

Research must consume explicit published dataset versions.

Preferred flow:

```text
Data Preparation
      ↓
Published DatasetRef
      ↓
Research Workflow
```

Research must not silently:

- download missing data,
- refresh provider data,
- mutate its input dataset,
- replace one dataset version with another.

Historical data resolution policies must be explicit.

Published dataset versions are immutable.

Dataset lifecycle transitions are explicit:

```text
WORKING → FINALIZED → PUBLISHED
```

`finalize()` and `publish()` are separate responsibilities.

A combined `finalize_and_publish()` workflow may exist, but it must perform and record both transitions explicitly.

Market datasets have identity, lifecycle, validation status and lineage independent of their physical storage format.

Raw or source retention is policy-driven rather than automatic.

Continuous futures are derived datasets and must preserve contract, roll and adjustment lineage.

---

### Modular Monolith

The initial architecture is a modular monolith.

The framework is developed and deployed as one system while preserving explicit internal boundaries.

Modules communicate through:

- public contracts,
- typed models,
- application services,
- events where asynchronous communication provides real value.

Microservices and distributed infrastructure remain deferred until independent deployment, scaling, reliability or ownership requirements justify them.

---

### Simplicity Before Scale

Architecture and technology decisions follow:

```text
Maximum Value / Minimum Complexity
```

Prefer:

- local processing before distributed processing,
- Parquet before large database clusters,
- DuckDB before Spark,
- direct calls for deterministic research,
- events for live execution where justified,
- explicit configuration before dynamic magic,
- composition before inheritance,
- typed contracts before implicit conventions.

Performance optimization must preserve correctness, reproducibility and maintainability.

---

## Architectural Principles

### Priority Order

The framework follows:

1. Correctness
2. Reproducibility
3. Maintainability
4. Simplicity
5. Performance
6. Scalability

A faster result is not useful when it is temporally invalid, statistically misleading or impossible to reproduce.

---

### Explicit Domain Ownership

Every model and behaviour has one owning domain.

A domain may consume another domain's public outputs.

It must not take ownership of another domain's logic.

---

### Separation of Concerns

The following responsibilities remain separate:

- market-data acquisition,
- normalization,
- validation,
- storage,
- dataset publication,
- analytical component calculation,
- model composition,
- research computation,
- research analytics,
- historical simulation,
- live execution,
- broker interaction,
- operational risk controls.

A single class or module must not accumulate unrelated responsibilities.

---

### Stable Dependency Direction

High-level domain logic must not depend directly on:

- provider SDKs,
- broker SDKs,
- database drivers,
- file formats,
- web frameworks,
- concrete infrastructure adapters.

Infrastructure implements domain and application contracts.

`src/` must not import concrete modules from `user_data/`.

User components are loaded through controlled discovery, registries, configuration or public contracts.

---

### Single Source of Truth

Every architectural concept must have one authoritative definition.

This includes:

- domain ownership,
- model semantics,
- workflow independence,
- dataset identity,
- component identity,
- configuration semantics,
- strategy composition,
- temporal availability rules.

Lower-level documents may extend these definitions but must not redefine them inconsistently.

---

### Reproducibility and Lineage

Every reproducible result must identify all material inputs, including where relevant:

- dataset identity and version,
- instrument mapping,
- time range,
- source, computation and evaluation timeframe,
- calendar and alignment policy,
- component definitions,
- component versions or implementation fingerprints,
- parameters,
- model definitions,
- execution assumptions,
- framework version,
- random seed.

Changing a material input creates a different result identity.

---

### Immutable Published Definitions

Published datasets and released model definitions are immutable.

A material change creates a new identity or version.

Historical results remain linked to the exact definitions and dataset versions used to produce them.

Working local components may remain mutable, but their research use requires implementation fingerprints.

---

### Persistent Intermediate Results

Deterministic and expensive intermediate results may be persisted when reusable.

Examples:

- derived market datasets,
- Market Analysis outputs,
- Market Model outputs,
- Signal Model occurrences,
- trade simulation results,
- research datasets.

Cache and persistence identity must include all material inputs.

Stale or incompatible results must never be reused silently.

---

### Independent Workflows

Signal Research, Strategy Research and Strategy Execution:

- consume shared domains,
- may reuse compatible artifacts,
- do not require each other's workflow output,
- maintain separate orchestration and persistence,
- never form one mandatory pipeline.

---

### Testability

Domain and model logic must be testable without:

- network access,
- live brokers,
- live market feeds,
- external databases,
- web servers.

External integrations require separate opt-in integration tests.

Temporal alignment, dataset lineage and model-expression evaluation require regression and invariant tests where appropriate.

---

### Controlled Extensibility

New implementations should be added through existing contracts.

Examples:

- new provider,
- new Market Analysis Feature,
- new Structure,
- new State,
- new Market Model,
- new Signal Model,
- new Exit Model,
- new Risk Model,
- new broker adapter.

Adding a component should not require modifying unrelated modules.

---

### Technology Independence

Domain concepts are not equivalent to implementation technologies.

Examples:

- `MarketBar` is not a Polars row,
- `DatasetRef` is not a file path,
- `Market Model` is not a YAML file,
- `Signal Occurrence` is not a database record,
- `Research Dataset` is not limited to DuckDB,
- `Order` is not a broker SDK object.

Technology choices surround stable domain concepts.

---

### No God Objects

The framework rejects objects that own entire workflows.

Prohibited examples:

- one Strategy class calculating analysis, entries, exits and risk,
- one DataManager owning providers, synchronization, validation, storage and research access,
- one workflow engine implementing domain-specific algorithms,
- one research service calculating all analytics internally,
- one Market or Signal Model hiding analytical dependencies.

---

## Domains

The framework contains five primary domains:

```text
Market
Market Analysis
Strategy
Research
Execution
```

Domains represent business responsibilities.

They are not workflows.

A workflow may consume multiple domains.

---

### Market Domain

#### Question

```text
What trusted market information is available?
```

#### Owns

- Instrument,
- MarketBar,
- MarketTrade,
- MarketQuote,
- future market-fact models,
- market dataset identity,
- dataset metadata and lifecycle,
- provider and importer contracts,
- normalization contracts,
- validation contracts,
- repository and access contracts,
- dataset publication and lineage contracts.

#### Does Not Own

- analytical interpretation,
- market states,
- Market Models,
- Signal Models,
- strategy composition,
- research analytics,
- broker execution.

#### Important Rules

- Provider schemas do not leak into domain logic.
- Bars are independent observations and may be provider-supplied or derived.
- Research consumes explicit published `DatasetRef` versions.
- Published dataset versions are immutable.
- Research does not trigger hidden data acquisition or mutation.

---

### Market Analysis Domain

#### Question

```text
What reusable analytical information can be derived from market-related data?
```

#### Owns

- Feature contracts and implementations,
- Structure contracts and implementations,
- State contracts and implementations,
- analytical component identity,
- dependency declarations,
- component registry,
- dependency graph,
- lazy execution,
- analytical caching,
- timeframe-aware requests,
- safe temporal alignment.

#### Does Not Own

- strategy-specific intent,
- Market Model definitions,
- Signal Model definitions,
- exit decisions,
- risk allocation,
- research conclusions,
- order execution.

#### Important Rule

Market Analysis describes market behaviour.

It does not decide how the description should be used as a trading hypothesis.

---

### Strategy Domain

#### Question

```text
How are trading hypotheses and complete strategies defined?
```

#### Owns

- Market Model definitions,
- Signal Model definitions,
- Signal Occurrence,
- Exit Model definitions,
- Risk Model definitions,
- Strategy Model definitions,
- logical expression contracts,
- model composition semantics,
- model identity and versioning contracts,
- strategy-related value objects.

#### Market Model

Defines a market-context hypothesis through a declarative expression over Market Analysis outputs.

#### Signal Model

Defines a trading-opportunity hypothesis through a declarative expression over Market Analysis outputs.

#### Signal Occurrence

A `SignalOccurrence` is the provider-independent result of evaluating a Signal Model.

It belongs to the Strategy Domain and preserves at least:

```text
signal_model_id
signal_model_version or definition_hash
instrument
detected_at
direction
reference_price
relevant analytical lineage
```

Research and Execution may wrap a Signal Occurrence with workflow-specific metadata, but they must not redefine its core semantics.

#### Exit Model

Defines when exposure should be reduced or closed.

#### Risk Model

Defines how much exposure or capital the strategy may request.

#### Strategy Model

Represents:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

#### Does Not Own

- market-data acquisition,
- analytical component implementation,
- research orchestration,
- backtesting infrastructure,
- broker integration,
- order routing.

---

### Research Domain

#### Question

```text
What can be learned from model definitions and historical data?
```

#### Owns

- Signal Research orchestration,
- Strategy Research orchestration,
- research run identity,
- Signal Research Datasets,
- Strategy Research Datasets,
- forward-return analysis,
- MFE and MAE analysis,
- event studies,
- conditional analysis,
- historical strategy simulation,
- walk-forward analysis,
- Monte Carlo analysis,
- robustness analysis,
- rankings,
- family analysis,
- research insights and reports.

#### Signal Research

Signal Research evaluates reusable analytical hypotheses without requiring both model types.

Supported research scopes include:

```text
Market Model only
Signal Model only
Market Model × Signal Model
```

Examples:

```text
Trend Market Model
Bullish Sweep Signal Model
Trend Market Model × Bullish Sweep Signal Model
```

Signal Research may therefore answer:

```text
How does a Market Model describe or segment future market behaviour?

How does a Signal Model behave without an additional market-context filter?

How does a Signal Model behave under a selected Market Model?
```

Signal Research does not require:

- both Market Model and Signal Model in the same experiment,
- Exit Model,
- Risk Model,
- position sizing,
- broker simulation,
- account state.

A research definition must state explicitly which model scope is being evaluated.

#### Strategy Research

Strategy Research evaluates complete Strategy Models:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

#### Historical Strategy Simulation

Batch or vectorized backtesting belongs to the Research Domain.

It is optimized for:

- large strategy spaces,
- reusable Strategy Research Datasets,
- explicit execution assumptions,
- historical performance analysis.

Historical strategy simulation is distinct from runtime replay.

#### Important Rule

Research computation and analytics remain separate.

Research does not own model definitions and does not redefine their behaviour.

---

### Execution Domain

#### Question

```text
How is a selected Strategy Model executed safely in a runtime environment?
```

#### Owns

- broker contracts and adapters,
- broker accounts,
- orders,
- fills,
- positions,
- order lifecycle,
- execution state,
- reconciliation,
- operational execution risk controls,
- execution persistence,
- recovery,
- monitoring and auditability.

#### Consumes

- selected Strategy Model definitions,
- live Market Data,
- required Market Analysis outputs,
- live configuration,
- account state.

#### Does Not Own

- Signal Research,
- Strategy Research,
- research datasets,
- research rankings,
- research reports,
- Market Analysis definitions,
- Strategy Model definitions.

> **As-built note (Sprint 054 T001):** the domain ownership above is
> confirmed built (broker contracts, orders, fills, positions, paper broker
> simulation). The vision document's "Runtime Modes" subsection (Replay
> Execution / Paper Execution / Live Execution) is classified MIXED — as of
> this sprint, `execution/modes.py` supports only the `DRY_RUN` execution
> mode; Replay and Live Execution are not yet implemented end-to-end. See
> `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §6.5 "Runtime Modes" and
> `SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`.

#### Important Rule

Execution must run without access to research workflow state.

---

## Domain Relationships

Allowed consumption relationships:

```text
Market
   │
   ▼
Market Analysis
   │
   ├──────────────► Strategy
   │                   │
   │                   ├──────────────► Research
   │                   │
   │                   └──────────────► Execution
   │
   ├──────────────────► Research
   └──────────────────► Execution

Market ───────────────► Research
Market ───────────────► Execution
```

This diagram represents allowed dependencies, not a mandatory runtime workflow.

Rules:

- Market Analysis consumes Market outputs.
- Strategy definitions consume Market Analysis contracts and outputs.
- Research consumes Market, Market Analysis and Strategy definitions.
- Execution consumes Market, Market Analysis and Strategy definitions.
- Strategy does not depend on Research.
- Execution does not depend on Research.
- Research and Execution do not depend on each other's workflow state.
- Market does not depend on higher-level domains.

---

## Framework and User Space

### Framework Space

```text
src/
```

contains reusable and maintainable implementation:

- domain contracts,
- generic infrastructure,
- reusable Market Analysis components,
- composition engines,
- research engines,
- execution infrastructure,
- public tests and documentation.

### User Space

```text
user_data/
```

contains user-owned assets:

- local and derived market data,
- working analytical components,
- candidate components,
- proprietary model definitions,
- research configurations,
- research results,
- reports,
- notebooks,
- private know-how.

Rules:

- `src/` never imports concrete modules from `user_data/`.
- User components are loaded through public contracts and controlled discovery.
- Framework tests run without proprietary user data.
- Framework upgrades do not overwrite user assets.
- User assets remain portable between compatible framework versions.

---

## Accepted Clarifications

The following decisions are accepted:

1. The third primary capability is named `Strategy Execution`.
2. Signal Research may evaluate:
   - Market Model only,
   - Signal Model only,
   - Market Model × Signal Model.
3. `SignalOccurrence` belongs to the Strategy Domain.
4. Batch/vectorized backtesting belongs to Research; Replay, Paper and Live modes belong to Execution. *(As-built note: only the `DRY_RUN` execution mode is implemented today; Replay and Live remain future — see "Execution Domain" above.)*
5. Position sizing remains part of the Risk Model in Version 1.
6. The shared analytical runtime is named `Market Analysis Engine`.
7. Dataset finalization and publication are separate lifecycle transitions.
8. Generic framework contracts and neutral model implementations may live in `src/`; proprietary compositions remain in `user_data/`.
9. Mutable local model definitions used in research require implementation or definition fingerprints.
10. Signal Research evaluates single analytical events through explicit one-condition Signal Models rather than bypassing model contracts.
11. Model expressions may use controlled `MarketFieldReference` objects but may not access arbitrary raw data structures directly.

---

## Final Architectural Statement

The Trading Research Framework is a modular monolith built around five domains and three independent system capabilities.

The framework must preserve:

```text
Market owns trusted market facts and dataset contracts.

Market Analysis owns reusable analytical descriptions of market behaviour.

Strategy owns declarative model definitions and strategy composition.

Research owns historical computation, reusable result datasets and analytics.

Execution owns runtime broker interaction and operational state.
```

The public framework provides reusable analytical and execution capabilities.

Private user space contains proprietary model composition, research configuration and results.

Signal Research, Strategy Research and Strategy Execution reuse the same foundations, but none is a required predecessor of another.

Research never forms one mandatory pipeline with execution.
