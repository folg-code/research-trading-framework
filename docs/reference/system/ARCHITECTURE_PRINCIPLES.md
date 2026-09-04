# Architecture Principles — As-Built Reference

> Extracted from the former `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`
> ("Core Philosophy", "Architectural Principles") by Sprint 055 T007
> (execute `docs/reference/` target IA), per the maintainer-approved
> `system/` re-cut in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. That file's own
> content originated in `docs/vision/ARCHITECTURE_FOUNDATIONS.md`, moved by
> Sprint 054 T004 (vision reclassification and reference layering) — see
> `docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
> for the original section-by-section classification and evidence. Content
> is reproduced verbatim from that move — this extraction does not rewrite
> any architectural decision, it only regroups by subject.
>
> This is the cross-cutting build-principles half of the former
> `ARCHITECTURE_FOUNDATIONS.md`. The domain-model half ("Domains", "Domain
> Relationships", "Framework and User Space", "Accepted Clarifications",
> "System Capabilities") now lives in
> [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md).

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

For this engine's full architecture (registry, DAG, lazy execution, cache
identity, execution context, output forms), see
[`MARKET_ANALYSIS_ARCHITECTURE.md`](MARKET_ANALYSIS_ARCHITECTURE.md).

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

For the full time/multitimeframe/alignment model, see
[`TIME_AND_ALIGNMENT.md`](TIME_AND_ALIGNMENT.md).

---

### Research Spaces Must Be Bounded and Observable (current-behavior portion)

> This subsection was classified MIXED by Sprint 054 T001. The
> framework-level distinction below (fixed selection / independent
> alternatives / bounded search space) and the progressive-research
> staircase are realized today through Robustness Research's bounded
> experiment/variant model. The planner-observability metadata (candidate
> count, applied constraints, estimated output size) named later in the
> vision section has **no code counterpart** and now lives in
> `docs/vision/RESEARCH_SPACE_AND_ANALYTICS.md` (merged from former
> `ARCHITECTURE_FOUNDATIONS.md` §4.10 by Sprint 055 T008).

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

For the enforced/unenforced distinction behind this rule (which directions
have a dedicated test and which are only spot-checked), see
[`DEPENDENCY_RULES.md`](DEPENDENCY_RULES.md).

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
