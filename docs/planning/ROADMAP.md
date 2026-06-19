# Trading Research Framework

# ROADMAP.md

## 1. Purpose

This document defines the strategic development roadmap of the Trading Research Framework.

It describes:

- major development phases,
- expected capabilities,
- dependencies between phases,
- completion criteria,
- major risks,
- intentionally deferred work.

The roadmap defines direction.

It is not:

- a detailed task list,
- a sprint plan,
- a replacement for GitHub Issues,
- a fixed delivery schedule,
- a promise that later phases will be implemented exactly as currently described.

Detailed planning should cover only the current and next phase.

---

## 2. Roadmap Principles

The roadmap follows these rules:

1. Deliver small vertical slices.
2. Validate architecture through implementation.
3. Keep the modular monolith until demonstrated needs justify distribution.
4. Preserve the separation between `src/` and `user_data/`.
5. Preserve the independence of:
   - Signal Research,
   - Strategy Research,
   - Strategy Execution.
6. Prefer correctness and reproducibility over raw speed.
7. Do not introduce infrastructure for hypothetical scale.
8. Update the roadmap when implementation produces new evidence.
9. Keep later phases directional rather than over-specified.
10. Treat rejected or deferred ideas as valid learning outcomes.

---

## 3. Phase Overview

```text
Phase 0 — Project Governance
        ↓
Phase 1 — Repository Foundation
        ↓
Phase 2 — Market Data MVP
        ↓
Phase 3 — Market Analysis Engine MVP
        ↓
Phase 4 — Market Analysis Components and Multitimeframe
        ↓
Phase 5 — Signal Research MVP
        ↓
Phase 6 — Strategy Research MVP
        ↓
Phase 7 — Robustness Research
        ↓
Phase 8 — Strategy Execution: Replay and Paper
        ↓
Phase 9 — Live and Multi-Account
```

The arrows represent capability dependencies.

They do not mean that Signal Research, Strategy Research and Strategy Execution form one runtime workflow.

---

# 4. Phase 0 — Project Governance

## Purpose

Create the minimum project-management system required for iterative development.

## Expected Capabilities

- strategic roadmap,
- concise current-status reporting,
- problem registry,
- idea inbox,
- technical-debt register,
- sprint planning and retrospectives,
- issue and PR conventions,
- ADR process,
- GitHub Project status model.

## Expected Outputs

```text
PROJECT_MANAGEMENT.md
ROADMAP.md
CURRENT_STATUS.md
PROBLEM_REGISTRY.md
IDEA_INBOX.md
TECHNICAL_DEBT.md
docs/planning/sprints/
docs/adr/
```

## Completion Criteria

- planning documents exist and have clear ownership,
- work statuses are defined,
- Definition of Ready and Definition of Done are defined,
- current and next phases can be planned without duplicating task state,
- GitHub Issues and Projects can become the operational source of truth,
- architectural decisions are separated from tasks and ideas.

**Progress (2026-06-19):** planning documents and Sprint 001 are in place. Remaining items: GitHub Project configuration, issue templates, and individual ADR files (started via `docs/adr/README.md`).

## Dependencies

None.

## Main Risks

- over-engineering project governance,
- duplicating status between Markdown and GitHub,
- creating detailed plans for distant phases,
- allowing planning files to become stale.

## Out of Scope

- detailed issues for every future phase,
- fixed dates for the full roadmap,
- productivity metrics based on lines of code or commit count.

---

# 5. Phase 1 — Repository Foundation

## Purpose

Create the implementation foundation shared by every domain.

## Expected Capabilities

- Python package structure,
- `src/` and `user_data/` separation,
- unit, integration and end-to-end test structure,
- Ruff formatting and linting,
- mypy type checking,
- pytest configuration,
- CI pipeline,
- core identifiers and errors,
- Timeframe and timestamp primitives,
- Clock contract,
- configuration loading,
- logging foundation,
- architecture-document references for AI agents.

## Primary Vertical Slice

```text
Repository
    ↓
Installable package
    ↓
Static checks
    ↓
Unit tests
    ↓
CI validation
```

## Completion Criteria

- project can be installed reproducibly,
- CI runs linting, formatting checks, typing and tests,
- domain packages exist without speculative implementation,
- `src/` does not import concrete `user_data/` modules,
- naive timestamps are rejected in core time models,
- one minimal configuration can be loaded and validated,
- framework tests do not require external systems.

## Dependencies

- Phase 0 planning conventions.

## Active Sprint

Sprint 001 implements this phase:

```text
docs/planning/sprints/SPRINT_001.md
```

## Main Risks

- creating empty abstractions for distant requirements,
- turning `core/` into a utilities dumping ground,
- adding web, database or distributed infrastructure prematurely,
- coupling configuration to implementation details.

## Out of Scope

- provider integrations,
- full Market Data workflows,
- Market Analysis Engine,
- research workflows,
- broker execution.

---

# 6. Phase 2 — Market Data MVP

## Purpose

Deliver the first complete, reproducible Market Data vertical slice.

## Primary Flow

```text
External OHLCV File
        ↓
Inspect
        ↓
Normalize to UTC
        ↓
Validate
        ↓
Persist in Parquet
        ↓
Register Dataset Version
        ↓
Finalize
        ↓
Publish
        ↓
Query Through Repository
```

## Expected Capabilities

- `Instrument`,
- `Timeframe`,
- `MarketBar`,
- `DatasetId`,
- `DatasetRef`,
- `DatasetMetadata`,
- dataset lifecycle,
- external file inspection,
- CSV or Parquet import,
- timestamp normalization,
- OHLCV validation,
- Parquet writer and repository,
- dataset registry,
- finalization,
- publication,
- historical query.

## Completion Criteria

- one OHLCV dataset can be imported end to end,
- provider-specific schema is normalized at the boundary,
- all timestamps are timezone-aware UTC,
- invalid OHLCV data produces explicit validation results,
- dataset identity is independent from file path,
- `WORKING → FINALIZED → PUBLISHED` is explicit,
- published versions are immutable,
- consumers query by `DatasetRef`,
- direct Parquet access from Research and Strategy is unnecessary,
- integration tests cover storage and publication.

## Dependencies

- repository foundation,
- core time models,
- configuration loading.

## Active Sprint

Sprint 002 implements this phase:

```text
docs/planning/sprints/SPRINT_002.md
```

## Main Risks

- ambiguous dataset identity,
- mixing storage paths with domain identity,
- hidden mutation of published datasets,
- incorrect gap assumptions,
- excessive small files,
- premature support for every provider and data type.

## Out of Scope

- live ingestion,
- provider synchronization,
- continuous futures construction,
- trades, quotes, DOM and options data,
- automatic missing-range fetching during Research.

---

# 7. Phase 3 — Market Analysis Engine MVP

## Purpose

Calculate reusable analytical components through explicit dependency contracts.

## Expected Capabilities

- generic Market Analysis component contract,
- Component Registry,
- `ComponentRequest`,
- dependency DAG,
- cycle detection,
- lazy execution,
- shared-node deduplication,
- component fingerprinting,
- cache identity,
- typed analytical results,
- one complete component vertical slice.

## Recommended First Components

```text
Feature:
ATR

Structure:
Pivot or Session Range

State:
simple volatility or trend state
```

Only one complete vertical slice is required initially.

## Primary Flow

```text
Published DatasetRef
        ↓
ComponentRequest
        ↓
Dependency Resolution
        ↓
Execution Plan
        ↓
Component Result
        ↓
Lineage and Cache Identity
```

## Completion Criteria

- a component declares all dependencies before execution,
- equivalent deterministic nodes are calculated once,
- hidden component calls inside `compute()` are rejected by convention and tests,
- cache identity includes dataset and implementation identity,
- working components can be loaded from controlled user space,
- research use of a working component stores an implementation fingerprint,
- the engine remains independent from Market Model and Signal Model semantics.

## Dependencies

- published Market Dataset access,
- stable time primitives,
- configuration contracts.

## Main Risks

- overbuilding graph infrastructure,
- forcing all payloads into one scalar representation,
- hidden data access from components,
- premature permanent directory taxonomy,
- cache reuse with incomplete identity.

## Out of Scope

- broad indicator library,
- advanced multitimeframe alignment,
- Signal Research,
- model ranking,
- distributed calculation.

---

# 8. Phase 4 — Market Analysis Components and Multitimeframe

## Purpose

Support timeframe-aware Market Analysis safely and reproducibly.

## Expected Capabilities

- source, computation and evaluation timeframe distinction,
- explicit resampling nodes,
- derived dataset lineage,
- `observed_at`,
- `available_at`,
- `LAST_CLOSED_BAR`,
- backward as-of alignment,
- intrabar component contract,
- Trading Session integration,
- Trading Calendar integration,
- controlled `MarketFieldReference`,
- Market Model expression evaluation,
- Signal Model expression evaluation,
- initial reusable Features, Structures and States.

## Suggested Initial Analytical Set

```text
Features:
- ATR
- slope
- wick ratio
- distance to level

Structures:
- Pivot
- HH / HL / LH / LL
- Session Range
- Liquidity Sweep

States:
- trend / range
- volatility state
- active session state
```

This is an initial research-enabling set, not a permanent mandatory taxonomy.

## Completion Criteria

- higher-timeframe final values are unavailable before bar close,
- resampling is explicit and reused,
- temporal alignment is covered by regression tests,
- DST and session boundaries are tested,
- Market Models and Signal Models remain declarative,
- models cannot access arbitrary DataFrames,
- one-condition Market and Signal Models are supported,
- framework and local components use the same public contracts.

## Dependencies

- Market Data MVP,
- Market Analysis Engine MVP,
- Time Model and calendars.

## Main Risks

- look-ahead bias,
- timestamp-boundary ambiguity,
- incorrect session semantics,
- mixing implementation patterns with output categories,
- excessive early taxonomy,
- divergence between Research and runtime semantics.

## Out of Scope

- unrestricted component grid searches,
- complete Strategy Research,
- live broker execution,
- advanced order-flow models.

---

# 9. Phase 5 — Signal Research MVP

## Purpose

Evaluate Market Models and Signal Models independently or together without requiring a complete Strategy Model.

## Supported Scopes

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

## Expected Capabilities

- explicit Signal Research configuration,
- bounded experiment expansion,
- Market Model result materialization,
- `SignalOccurrence`,
- forward-return calculation,
- MFE and MAE,
- event frequency,
- persistent Signal Research Dataset,
- reusable analytics,
- sample-size filters,
- timeframe and period comparisons,
- computation/analytics separation.

## Primary Flows

```text
Market Model only
        ↓
Future Market Behaviour
```

```text
Signal Model only
        ↓
SignalOccurrence
        ↓
Forward Behaviour
```

```text
Market Model × Signal Model
        ↓
Conditional Signal Behaviour
```

## Completion Criteria

- all three scopes work explicitly,
- Signal Research does not require Exit or Risk Models,
- new analytics do not rerun unchanged computation,
- stored datasets remain queryable without loading implementation classes,
- independent experiment alternatives are not confused with logical `OR`,
- shared analytical dependencies are reused,
- run identity includes datasets, models, fingerprints and time semantics.

## Dependencies

- model expression evaluation,
- Market Analysis results,
- published datasets,
- persistent Research Dataset contracts.

## Main Risks

- accidental Cartesian-product growth,
- weak lineage,
- multiple-testing blindness,
- recomputing results for every report,
- treating one good result as validated edge.

## Out of Scope

- complete strategy PnL,
- position sizing,
- broker fill simulation,
- deployment decisions,
- automatic strategy promotion.

---

# 10. Phase 6 — Strategy Research MVP

## Purpose

Evaluate complete Strategy Models under explicit historical and execution assumptions.

## Strategy Composition

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

## Expected Capabilities

- Exit Model contract,
- Risk Model contract,
- Strategy Model definition,
- batch or vectorized backtest,
- order and fill simulation assumptions,
- commissions and slippage,
- trade-level results,
- position and equity history,
- persistent Strategy Research Dataset,
- strategy metrics,
- strategy rankings with explicit eligibility filters,
- family grouping.

## Completion Criteria

- complete Strategy Models can be simulated,
- simulation assumptions are part of run identity,
- raw trade-level results are preserved where practical,
- rankings state objective and eligibility rules,
- Strategy Research does not require a Signal Research run,
- shared upstream Market Analysis and signal artifacts can be reused,
- Replay Execution remains a separate capability.

## Dependencies

- Signal and Market Model contracts,
- SignalOccurrence,
- Research Dataset infrastructure,
- deterministic upstream reuse.

## Main Risks

- monolithic backtest engine,
- unclear fill assumptions,
- insufficient raw-result retention,
- ranking by one metric,
- conflating batch backtest with runtime replay.

## Out of Scope

- operational broker reconciliation,
- live account state,
- multi-account execution,
- full robustness validation.

---

# 11. Phase 7 — Robustness Research

## Purpose

Assess candidate stability and reduce overfitting risk.

## Expected Capabilities

- walk-forward analysis,
- out-of-sample evaluation,
- Monte Carlo methods,
- parameter perturbation,
- timeframe sensitivity,
- cost sensitivity,
- delayed and missed trade simulation,
- cross-asset evaluation,
- Market Model and Strategy Family analysis,
- complexity metrics,
- multiple-testing metadata,
- Pareto or multi-objective evaluation.

## Completion Criteria

- robustness methods record their assumptions,
- research spaces preserve generated and evaluated candidate counts,
- family analysis identifies isolated optima,
- complexity is measurable,
- top ranking is not treated as validation,
- validation outputs are stored separately from base computation.

## Dependencies

- persistent Strategy Research Datasets,
- stable strategy metrics,
- experiment-family identity.

## Main Risks

- false confidence from sophisticated statistics,
- misuse of Monte Carlo,
- data leakage between train and test periods,
- uncontrolled optimization,
- robustness analytics coupled to one strategy type.

## Out of Scope

- automatic live deployment,
- universal hard-coded candidate score,
- distributed research infrastructure without evidence.

---

# 12. Phase 8 — Strategy Execution: Replay and Paper

## Purpose

Run selected Strategy Models with runtime-style semantics without real-money execution.

## Expected Capabilities

- Replay Clock,
- Replay Execution,
- Paper Execution,
- runtime Market Analysis updates,
- SignalOccurrence processing,
- strategy decisions,
- order lifecycle,
- partial fills,
- positions,
- operational risk controls,
- persistence,
- reconciliation,
- recovery,
- monitoring.

## Completion Criteria

- replay consumes published historical data,
- paper mode consumes live normalized market data,
- Strategy Model is execution-mode independent,
- order transitions are explicit,
- duplicate events are handled safely,
- runtime state survives restart where required,
- broker-like state can be reconciled,
- Research workflow state is not required.

## Dependencies

- stable Strategy Model contracts,
- Market Analysis runtime semantics,
- Event System where justified,
- replay data access,
- execution persistence.

## Main Risks

- divergence between research and runtime behaviour,
- hidden event ordering assumptions,
- insufficient idempotency,
- in-memory-only state,
- operational risk logic leaking into Strategy Risk Models.

## Out of Scope

- real broker orders,
- multi-account orchestration,
- prop-firm-specific controls.

---

# 13. Phase 9 — Live and Multi-Account

## Purpose

Support safe operational execution with real brokers and eventual account scaling.

## Expected Capabilities

- broker adapters,
- live order submission,
- account state,
- durable execution records,
- reconnect and recovery,
- reconciliation,
- monitoring and alerts,
- kill switches,
- account-specific operational limits,
- multi-account coordination,
- strategy allocation,
- audit trails.

## Completion Criteria

To be defined only after Replay and Paper Execution validate runtime contracts.

Minimum future requirements include:

- fail-safe live behaviour,
- no silent order or fill loss,
- deterministic reconciliation policy,
- account isolation,
- explicit deployment and rollback process,
- operational observability.

## Dependencies

- successful replay and paper validation,
- stable broker contracts,
- mature operational controls,
- deployment architecture.

## Main Risks

- financial loss,
- broker/provider inconsistency,
- stale data,
- duplicate orders,
- partial failures across accounts,
- insufficient recovery and monitoring.

## Out of Scope Until Phase Entry

- distributed execution services,
- 50+ account coordination,
- Kubernetes,
- Kafka,
- global high-availability architecture.

---

# 14. Cross-Phase Architectural Gates

A phase must not be considered complete if it violates these gates.

## Reproducibility Gate

Results identify all material:

- datasets,
- versions,
- configurations,
- component identities,
- model identities,
- time semantics,
- execution assumptions.

## Temporal Correctness Gate

No result uses information before its legal `available_at`.

## Domain Ownership Gate

Responsibilities remain in their owning domains.

## Workflow Independence Gate

Signal Research, Strategy Research and Strategy Execution do not require each other's workflow state.

## User-Space Gate

Proprietary definitions and data remain in `user_data/`.

## Complexity Gate

New infrastructure solves a demonstrated problem.

## Test Gate

Critical contracts have unit, integration, regression or workflow tests as appropriate.

---

# 15. Deferred Capabilities

The following remain deferred until evidence justifies them:

```text
Microservices
Kubernetes
Kafka
Spark
Distributed Market Analysis Engine
Multi-node research scheduler
Dedicated feature-store product
Remote component registry
Visual workflow or DAG editor
Full event sourcing
Full DOM / L2 model
Options snapshot model
Automatic ML feature vector layer
Separate Position Sizing Model
Distributed Strategy Execution
```

Deferred does not mean rejected.

Each item requires a decision trigger, design review and usually an ADR before implementation.

---

# 16. Roadmap Review

Review the roadmap:

- at the end of every phase,
- after a material architectural decision,
- after evidence invalidates an assumption,
- when a critical problem changes priorities,
- before detailed planning of the next phase.

Do not rewrite historical phase outcomes.

Record actual outcomes in sprint reviews and `CURRENT_STATUS.md`.
