# Trading Research Framework

# PRODUCT_DIRECTION.md

> **Sprint 055 T008 note:** this file is new. It consolidates the only
> genuinely product-level, aspirational material that was orphaned inside
> two engineering documents dissolved by this sprint —
> `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §1 (Purpose) and §3 (Vision),
> and `docs/vision/WORKFLOWS_AI_ADR.md` §1 (Purpose) and §8 (Final
> Contract). Content below is preserved verbatim from those sections; only
> this header and the provenance/pending-move notes are newly authored.
> See `docs/planning/sprints/SPRINT_055_T002_VISION_TARGET_IA.md` and
> `SPRINT_055_T004_DECISIONS.md` for the rationale.

---

## 1. Purpose

*(Merged from: `ARCHITECTURE_FOUNDATIONS.md` §1, `WORKFLOWS_AI_ADR.md` §1)*

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

This document also defines:

- the Signal Research workflow,
- the Strategy Research workflow,
- the Strategy Execution workflow,
- the AI Agent Contract,
- the Architectural Decision Record process.

The framework supports three independent system capabilities:

```text
Signal Research
Strategy Research
Strategy Execution
```

These capabilities share domains, models, analytical components and infrastructure contracts.

They are not stages of one mandatory pipeline.

A workflow consumes domain components.

A workflow does not redefine domain ownership.

---

## 2. Vision

*(Classified MIXED by Sprint 054 T001 — this section is written throughout
in prospective/aspirational language ("should support", "future
extensions") even though some of the listed capabilities already exist. Left
in full here rather than split bullet-by-bullet; see
`docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
§3 for which bullets already have a code counterpart, e.g. crypto data and
ML/tree-based estimators, versus which do not, e.g. multi-asset/multi-account
execution, distributed computation, portfolio research.)*

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

## 3. Final Contract

*(From `WORKFLOWS_AI_ADR.md` §8. Classified MIXED by Sprint 054 T003b — every
substantive claim below is a restatement of content classified elsewhere in
the dissolved vision files; its MIXED status is inherited from the
confirmed partial-execution-mode finding now recorded in
`EXECUTION_RUNTIME_FUTURE.md` — "Strategy Execution runs selected Strategy
Models in Replay, Paper or Live modes" only holds for one mode (`DRY_RUN`)
today.)*

The framework preserves three independent capabilities:

```text
Signal Research
Strategy Research
Strategy Execution
```

They share:

```text
Market
Market Analysis
Strategy Definitions
Time
Configuration
Infrastructure Contracts
```

They do not share mandatory workflow state.

The implementation must ensure that:

```text
Signal Research evaluates Market Models, Signal Models or both.

Strategy Research evaluates complete Strategy Models.

Strategy Execution runs selected Strategy Models in Replay, Paper or Live modes.

Research Computation produces reusable datasets.

Research Analytics interprets stored datasets.

AI agents preserve architecture rather than inventing it.

ADRs preserve the reasoning behind significant decisions.
```

Every future workflow, implementation and architectural decision must remain consistent with this contract.

---

## 4. Content that moved elsewhere

- **Composition Over Inheritance** (`ARCHITECTURE_FOUNDATIONS.md` former
  §5.5, a repo-wide coding-style convention, not product direction) is
  **pending a Cursor-side move** to `.cursor/rules/ARCHITECTURE_CONTROL.md`
  per Sprint 055 T004 — this is out of Sprint 055's scope (same deferred
  Cursor-side pass as Sprint 053 T008). The content itself was not deleted;
  it is parked in `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` pending
  that move so it is not lost.
- **Controlled Technology Adoption** (`ARCHITECTURE_FOUNDATIONS.md` former
  §5.14, a governance rule about when an ADR is required) was folded into
  `docs/adr/README.md`'s "When an ADR is required" section per Sprint 055
  T004/T008.
- The AI Agent Contract (`WORKFLOWS_AI_ADR.md` former §6) and the ADR
  process (`WORKFLOWS_AI_ADR.md` former §7) were already consolidated into
  `AGENTS.md` / `.cursor/rules/ARCHITECTURE_CONTROL.md` and
  `docs/adr/README.md` respectively by Sprint 054 T006a/T006b.
