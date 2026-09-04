# Domain Model — As-Built Reference

> Extracted from the former `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`
> ("System Capabilities", "Domains", "Domain Relationships", "Framework and
> User Space", "Accepted Clarifications", "Final Architectural Statement")
> by Sprint 055 T007 (execute `docs/reference/` target IA), per the
> maintainer-approved `system/` re-cut in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. That file's own
> content originated in `docs/vision/ARCHITECTURE_FOUNDATIONS.md`, moved by
> Sprint 054 T004 (vision reclassification and reference layering). The
> sections below were classified **CURRENT** (or are the current-behavior
> portion of a section that was classified **MIXED**) against the codebase
> as of 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references. Content is reproduced verbatim from that move — this
> extraction does not rewrite any architectural decision, it only regroups
> by subject.
>
> This is the domain-model half of the former `ARCHITECTURE_FOUNDATIONS.md`.
> The cross-cutting build-principles half ("Core Philosophy" and
> "Architectural Principles") now lives in
> [`ARCHITECTURE_PRINCIPLES.md`](ARCHITECTURE_PRINCIPLES.md).
>
> Future-facing, ambiguous-status, and not-yet-built content (the promotion
> lifecycle in former §4.12, the "Composition Over Inheritance" style rule in
> former §5.5, and the Replay/Live Execution runtime modes in former §6.5)
> was dissolved by Sprint 055 T008 into
> [`docs/vision/COMPONENT_PROMOTION_LIFECYCLE.md`](../../vision/COMPONENT_PROMOTION_LIFECYCLE.md)
> (promotion lifecycle), `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md`
> (Composition Over Inheritance, pending a Cursor-side move), and
> [`docs/vision/EXECUTION_RUNTIME_FUTURE.md`](../../vision/EXECUTION_RUNTIME_FUTURE.md)
> (runtime modes).

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
> `docs/vision/EXECUTION_RUNTIME_FUTURE.md` (merged from former
> `ARCHITECTURE_FOUNDATIONS.md` §6.5 "Runtime Modes" by Sprint 055 T008) and
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

For the enforced/unenforced distinction behind this diagram (which
directions have a dedicated test and which are only spot-checked), see
[`DEPENDENCY_RULES.md`](DEPENDENCY_RULES.md).

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
