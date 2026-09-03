# Trading Research Framework

# ARCHITECTURE_FOUNDATIONS.md

> **Sprint 054 T004 note:** most of this document's sections were classified
> CURRENT (already built, verified against `src/trading_framework/`) by
> `docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
> and have moved to
> [`docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`](../reference/system/ARCHITECTURE_FOUNDATIONS.md).
> What remains here is future-facing, ambiguous-status, or the still-future
> portion of a mixed section — see the classification doc for the full
> section-by-section reasoning and evidence before assuming anything below
> is or is not built.

## 1. Purpose

This document defines the architectural foundations of the Trading Research Framework.

It establishes:

- the common architectural language,
- system and domain boundaries,
- ownership of responsibilities,
- dependency direction,
- framework and user-space separation,
- research and execution independence,
- non-negotiable design principles.

It is the highest-level architectural contract for:

- framework maintainers,
- contributors,
- research users,
- strategy developers,
- AI coding agents.

More detailed technical, workflow and module documents may extend these foundations, but they must not contradict them.

---

## 3. Vision

*(Classified MIXED by T001 — this section is written throughout in
prospective/aspirational language ("should support", "future extensions")
even though some of the listed capabilities already exist. Left in full
here rather than split bullet-by-bullet; see
`SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md` §3 for which
bullets already have a code counterpart, e.g. crypto data and ML/tree-based
estimators, versus which do not, e.g. multi-asset/multi-account execution,
distributed computation, portfolio research.)*

The Trading Research Framework is a modular platform for systematic trading research and strategy execution.

It is not:

- a collection of monolithic strategy classes,
- an indicator-to-order pipeline,
- a single mandatory research-to-execution workflow,
- tied to one asset class, broker, provider, timeframe or strategy style.

The framework should support:

- futures,
- forex,
- equities,
- indices,
- commodities,
- cryptocurrencies,
- CFDs,
- additional market-data types when required.

The framework should make it possible to:

- acquire, normalize, validate and version heterogeneous market data,
- develop reusable tools for describing market behaviour,
- compose Market Models and Signal Models from reusable analytical outputs,
- compose complete Strategy Models from independent components,
- research signals independently from complete strategies,
- research complete strategies under explicit execution assumptions,
- persist reusable computation results,
- analyse stored results without unnecessary recomputation,
- execute selected Strategy Models without loading research workflow state,
- scale computation and execution only when demonstrated requirements justify it.

The architecture should support future extensions such as:

- statistical models,
- machine learning,
- tree-based models,
- feature selection,
- automated research,
- portfolio research,
- order-flow and market-microstructure analysis,
- options-derived context,
- multi-asset and multi-account execution,
- distributed computation when required.

These extensions must not require fundamental redesign of the core domain model.

---

## 4. Core Philosophy

### 4.10 Research Spaces Must Be Bounded and Observable (planner-observability portion)

*(Classified MIXED by T001. The framework-level distinction between fixed
selection / independent alternatives / bounded search space, and the
progressive-research staircase, are already realized — see
[`docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`](../reference/system/ARCHITECTURE_FOUNDATIONS.md#research-spaces-must-be-bounded-and-observable-current-behavior-portion).
The planner-observability metadata below has no matching field anywhere in
`src/` as of this sprint.)*

Before large computation, the planner should expose where possible:

- candidate count,
- unique dependency count,
- reused nodes,
- new nodes,
- applied constraints,
- estimated output size.

Large search spaces require visible multiple-testing metadata.

---

### 4.12 Local Component Development and Promotion

*(Classified MIXED by T001 — as-built status unclear/partial. The
underlying identity primitives (`component_id`, `definition_hash`,
`resolved_parameters`) are pervasively implemented elsewhere in the
codebase and already documented as CURRENT in
`docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`. The five-stage
promotion lifecycle and the `reproducibility_status`/`implementation_hash`
fields described below have zero code counterpart as of this sprint — see
`SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md` §4.12 for the
evidence.)*

Market Analysis components may be developed locally before becoming maintained framework components.

Suggested lifecycle:

```text
Local Working Component
        ↓
Experimental Component
        ↓
Validated Candidate
        ↓
Promoted Framework Component
        ↓
Released Framework Component
```

Working components may change freely and do not require formal public versioning.

However, research using a working component must preserve an implementation fingerprint.

Suggested working identity:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

A component may be promoted into the framework when it is:

- stable,
- reusable,
- strategy-independent,
- tested,
- documented,
- governed by an explicit contract,
- ready for compatibility maintenance.

Formal component versioning begins when the component becomes part of the maintained framework contract.

The same fingerprint rule applies to mutable local model definitions used in research, including:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

Their experimental identity should include:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

Not every completed component must become public.

---

## 5. Architectural Principles

### 5.5 Composition Over Inheritance

*(Classified AMBIGUOUS by T001 — as-built status unclear as of Sprint 054;
see `SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md` §5.5. This
is a codebase-wide style convention that would require a broader structural
audit than T001's grep-level verification to confirm or refute.)*

Prefer:

- composition,
- dependency injection,
- immutable value objects,
- Protocols,
- explicit expression trees,
- registries,
- validated configuration.

Avoid:

- deep inheritance trees,
- shared mutable base classes,
- hidden dependencies,
- global service locators,
- runtime monkey patching.

---

### 5.14 Controlled Technology Adoption

A new technology may be introduced only when it solves a demonstrated problem.

A material decision must include:

- problem statement,
- expected benefit,
- operational cost,
- migration cost,
- alternatives,
- rollback strategy.

Technology must not be introduced solely for novelty or anticipated scale.

---

## 6. Domains

### 6.5 Execution Domain — Runtime Modes

*(Classified MIXED by T001. Domain ownership — broker contracts, orders,
fills, positions, paper broker simulation — is CURRENT and has moved to
[`docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`](../reference/system/ARCHITECTURE_FOUNDATIONS.md#execution-domain).
The Runtime Modes below remain only partially built: as of this sprint,
`execution/modes.py` supports only the `DRY_RUN` execution mode. Replay
Execution and Live Execution, as described below, are not yet supported
end-to-end.)*

Execution may support:

```text
Replay Execution
Paper Execution
Live Execution
```

Replay Execution:

- uses historical published data,
- uses a Replay Clock,
- follows runtime-style order, fill and position semantics,
- validates research/runtime parity.

Paper Execution:

- uses live market data,
- uses simulated broker interaction,
- belongs to Execution rather than Research.

Live Execution:

- interacts with a real broker account.

These modes are distinct from batch or vectorized backtesting owned by Research.
