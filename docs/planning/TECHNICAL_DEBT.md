# Trading Research Framework

# TECHNICAL_DEBT.md

## 1. Purpose

This register records known implementation debt that has been consciously accepted.

Technical debt is different from:

- an unresolved architectural problem,
- an unvalidated idea,
- a bug that violates expected behaviour,
- intentionally deferred future functionality.

An item belongs here only when:

1. a simpler or incomplete implementation is consciously accepted,
2. the limitation is understood,
3. the current system may still operate correctly within documented boundaries,
4. future remediation cost or risk is known.

Because the project is currently pre-implementation, this register initially contains mostly planned debt boundaries and no large body of accumulated code debt.

---

## 2. Statuses

```text
ACCEPTED
PLANNED_REPAYMENT
IN_PROGRESS
REPAID
OBSOLETE
```

---

## 3. Priority

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Priority reflects repayment importance.

---

## 4. Debt Entry Template

```markdown
## TD-XXX — Title

Status:
Priority:
Domain:
Introduced:
Target Review:
Owner:

### Accepted Shortcut

...

### Reason

...

### Consequences

...

### Safe Operating Boundary

...

### Repayment Trigger

...

### Repayment Direction

...

### Related Problems

- ...

### Related Tasks

- ...
```

---

# 5. Accepted Technical Debt

## TD-001 — Architecture Decisions Are Consolidated Before Individual ADR Files Exist

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Governance / Architecture
Introduced: 2026-06-19
Target Review: Phase 0 completion
Owner: Unassigned
```

### Accepted Shortcut

Architectural decisions are currently documented in consolidated architecture files instead of individual numbered ADRs.

### Reason

The architecture was evolving rapidly and consolidating decisions first reduced fragmentation.

### Consequences

- historical alternatives are less visible,
- individual decisions are harder to supersede cleanly,
- contributors must inspect large documents.

### Safe Operating Boundary

No material architectural change should be implemented without checking the consolidated documents.

### Repayment Trigger

Before implementation moves beyond repository foundation.

### Repayment Direction

Create the initial ADR set and cross-reference it from architecture documents.

### Related Problems

- PRB-016.

---

## TD-002 — Planning State Is Maintained in Markdown Before GitHub Project Setup

```text
Status: ACCEPTED
Priority: LOW
Domain: Governance
Introduced: 2026-06-19
Target Review: Phase 0 completion
Owner: Unassigned
```

### Accepted Shortcut

Current status, problems and ideas are stored in Markdown before GitHub Issues and Projects become the operational source of truth.

### Reason

The repository governance structure is still being created.

### Consequences

- manual updates,
- possible status drift,
- no automated issue linking.

### Safe Operating Boundary

Do not duplicate detailed task state in multiple Markdown files.

### Repayment Trigger

Repository and GitHub Project are initialized.

### Repayment Direction

Move operational task state to GitHub and retain Markdown for stable rules and summaries.

---

## TD-003 — Initial Market Analysis Module Uses a Minimal Directory Structure

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Analysis
Introduced: Planned for Phase 3
Target Review: After first 5–10 stable components
Owner: Unassigned
```

### Accepted Shortcut

Begin with:

```text
market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

instead of immediately creating separate permanent directories for every semantic category and engine capability.

### Reason

The conceptual taxonomy is known, but the practical component volume is not.

### Consequences

- temporary mixed component directory,
- later file moves may be required.

### Safe Operating Boundary

Every component must still declare whether its output is a Feature, Structure or State.

### Repayment Trigger

The module becomes difficult to navigate or stable clusters emerge.

### Repayment Direction

Split into justified directories without changing domain semantics.

---

## TD-004 — Version 1 Keeps Position Sizing Inside the Risk Model

```text
Status: ACCEPTED
Priority: LOW
Domain: Strategy
Introduced: Architecture baseline
Target Review: Phase 6 or later
Owner: Unassigned
```

### Accepted Shortcut

Do not create a separate Position Sizing Model in Version 1.

### Reason

Independent composition and versioning are not yet demonstrated requirements.

### Consequences

Some Risk Models may contain both capital constraints and sizing logic.

### Safe Operating Boundary

Risk responsibilities must remain strategy-level and separate from operational execution risk controls.

### Repayment Trigger

Sizing variants require independent research, composition or execution reuse.

### Repayment Direction

Introduce a separate contract through an ADR and migration plan.

---

## TD-005 — Version 1 Uses an In-Memory Event Bus

```text
Status: ACCEPTED
Priority: LOW
Domain: Events / Execution
Introduced: Planned for Phase 8
Target Review: Before Live Execution
Owner: Unassigned
```

### Accepted Shortcut

Use an in-process EventBus rather than Redis, Kafka or another durable broker.

### Reason

The initial system is a modular monolith and does not require distributed messaging.

### Consequences

- no process-independent durability,
- no horizontal consumer scaling,
- restart loses non-persisted in-flight events.

### Safe Operating Boundary

Critical Execution state must be persisted independently.

The EventBus must not be treated as the system of record.

### Repayment Trigger

Multiple processes, durable replay or independent services become required.

### Repayment Direction

Evaluate a distributed broker through an ADR.

---

## TD-006 — Historical Storage Uses Local Parquet Before a Dedicated Data Platform

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Data / Infrastructure
Introduced: Architecture baseline
Target Review: After measured storage bottlenecks
Owner: Unassigned
```

### Accepted Shortcut

Use local Parquet, optional DuckDB and metadata storage rather than a distributed data platform.

### Reason

This maximizes value with minimum operational complexity.

### Consequences

- limited multi-user concurrency,
- local-machine storage constraints,
- manual distribution across machines.

### Safe Operating Boundary

Dataset identity and lineage remain independent from physical paths.

### Repayment Trigger

One-machine storage, query or coordination limits are repeatedly exceeded.

### Repayment Direction

Assess object storage, shared catalogues or distributed query engines using measured requirements.

---

## TD-007 — Initial Trading Calendar May Wrap an External Library

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Time / Market
Introduced: Planned for Phase 2 or 4
Target Review: After CME vertical slice
Owner: Unassigned
```

### Accepted Shortcut

Use an adapter around an existing calendar library rather than implementing full exchange calendars internally.

### Reason

Exchange holiday and shortened-session logic is complex and not a core differentiator.

### Consequences

- external library behaviour and updates become dependencies,
- unsupported markets may need overrides,
- reproducibility requires calendar-version metadata.

### Safe Operating Boundary

Domain and application layers depend only on framework calendar contracts.

### Repayment Trigger

Required markets are unsupported or external behaviour cannot be versioned reliably.

### Repayment Direction

Add framework-owned overrides or selected internal calendar definitions.

---

## TD-008 — Initial Research Planner Uses Conservative Static Limits

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Research
Introduced: Planned for Phase 5
Target Review: After measured research workloads
Owner: Unassigned
```

### Accepted Shortcut

Use static candidate-count and model-complexity limits before dynamic cost estimation is available.

### Reason

A simple hard boundary protects against accidental explosion.

### Consequences

- limits may be too strict or too permissive,
- no accurate runtime estimate.

### Safe Operating Boundary

Overrides must be explicit and visible.

The planner must never silently prune requested experiments.

### Repayment Trigger

Measured workloads provide enough data for cost estimation.

### Repayment Direction

Implement preflight resource estimates and configurable policy tiers.

---

## TD-009 — Initial Strategy Backtest Supports a Limited Fill Model

```text
Status: ACCEPTED
Priority: HIGH
Domain: Research
Introduced: Planned for Phase 6
Target Review: Before robustness claims
Owner: Unassigned
```

### Accepted Shortcut

The first batch/vectorized backtest should support a deliberately limited, explicit fill model rather than full broker realism.

### Reason

Full execution simulation would significantly expand Phase 6 scope and blur the Research/Execution boundary.

### Consequences

- some strategy types cannot be evaluated accurately,
- results depend strongly on documented assumptions,
- no claim of live parity is allowed.

### Safe Operating Boundary

Unsupported orders, partial fills and intrabar ambiguity must fail or be explicitly excluded.

### Repayment Trigger

A selected strategy requires more realistic order semantics.

### Repayment Direction

Add simulation capabilities incrementally while preserving assumptions in run identity.

---

## TD-010 — Documentation Consistency Is Reviewed Manually Before Automation

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Documentation / Governance
Introduced: 2026-06-19
Target Review: Phase 1
Owner: Unassigned
```

### Accepted Shortcut

Use manual review and simple text searches before implementing documentation linting or architecture checks.

### Reason

Document conventions are still stabilizing.

### Consequences

- stale terminology may remain,
- heading numbering and references may drift.

### Safe Operating Boundary

Architecture-changing work must update all affected documents.

### Repayment Trigger

The documentation set stabilizes and repository CI exists.

### Repayment Direction

Add lightweight checks for deprecated terms, required files and broken internal references.

---

## TD-011 — Historical Query Returns List of MarketBar Objects

```text
Status: ACCEPTED
Priority: HIGH
Domain: Market Data
Introduced: Sprint 002 (2026-06)
Target Review: Before large-scale batch analysis or Sprint 004 MTF spike completion
Owner: Unassigned
```

### Accepted Shortcut

`query_historical` materializes results as `list[MarketBar]` — one Python object per bar.

### Reason

Sprint 002 prioritized semantic clarity and testability over columnar throughput for MVP fixtures.

### Consequences

- high memory and construction cost for multi-year 1m data,
- mandatory conversion before Polars/NumPy vectorized analysis,
- Sprint 003 `AnalysisDataView.from_bars()` adds another conversion step.

### Safe Operating Boundary

Use committed fixtures and modest bar counts in CI. Do not assume million-row in-memory lists are production-viable.

### Repayment Trigger

Sprint 004 Polars resample path or first production-scale dataset import.

### Repayment Direction

Add columnar batch return type (`MarketDataBatch` / `pl.LazyFrame` with metadata) alongside or instead of list materialization for analytical paths.

### Related Problems

- PRB-004 (user_data discovery — separate concern).

### Related Tasks

- Sprint 004 T001 spike
- `docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md` §5.1

---

## TD-012 — Decimal OHLCV in Market Data with float64 Analysis Conversion

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Data / Market Analysis
Introduced: Sprint 002 (MarketBar) + Sprint 003 (AnalysisDataView float64)
Target Review: When analytical backend standardizes on Polars-native types
Owner: Unassigned
```

### Accepted Shortcut

Market Data stores prices as `Decimal`; Market Analysis adapters consume `float64`.

### Reason

Domain-safe storage vs research-default computation dtype (D-027).

### Consequences

- conversion on every analysis run,
- impedance with Polars/TA-Lib native types,
- two precision semantics to document.

### Safe Operating Boundary

Research/backtest paths only; not used for order accounting without separate money types.

### Repayment Trigger

Polars-first batch pipeline adopted for query + analysis boundary.

### Repayment Direction

Analytical OHLCV as float64 or scaled integer at storage boundary; reserve Decimal for execution/accounting.

### Related Tasks

- Architecture Simplification Review §2.2, §3.2

---

## TD-013 — Multi-Implementation Registry Before Second Backend

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Analysis
Introduced: Sprint 003
Target Review: When second backend (Polars-native or TA-Lib) is committed
Owner: Unassigned
```

### Accepted Shortcut

`ComponentRegistry` resolves multiple implementations per component with explicit/default policy; only NumPy adapter is production-ready.

### Reason

Vision doc D-004/D-005 anticipated interchangeable backends before MVP delivery.

### Consequences

- resolver and dual identity axis maintained without interchange benefit,
- higher mental load for contributors,
- tests cover resolution paths rarely used.

### Safe Operating Boundary

Register only NumPy implementations in CI. Do not add resolver features until a second backend ships.

### Repayment Trigger

TA-Lib extra (S003-T027) or Polars-native component path lands with real interchange need.

### Repayment Direction

Simplify to `ComponentId → ComponentDefinition` if second backend never materializes; otherwise keep registry but document interchange contract.

---

## TD-014 — Separate ResultStore, Workspace and In-Plan ExecutionCache

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Analysis
Introduced: Sprint 003
Target Review: Sprint 004 executor changes or persistent cache work
Owner: Unassigned
```

### Accepted Shortcut

Three execution-scoped structures: `AnalysisResultStore`, `AnalysisWorkspace`, `ExecutionCache`.

### Reason

Four-layer model from workspace vision doc; cache ADR-MA-008 for exact-match deduplication.

### Consequences

- overlapping responsibilities for single-plan batch MVP,
- duplicate lookup paths,
- more surface area for MTF extensions.

### Safe Operating Boundary

Single sequential plan per run; no cross-run cache; no persistent workspace.

### Repayment Trigger

Cross-run cache, partial reruns, or persistent derived results require distinct lifecycles.

### Repayment Direction

Evaluate consolidation into `ExecutionState: dict[NodeKey, ComponentResult]` when touching executor without breaking ADR semantics.

---

## TD-015 — AnalysisDataView Map-of-Arrays Instead of Columnar Frame

```text
Status: ACCEPTED
Priority: HIGH
Domain: Market Analysis
Introduced: Sprint 003 (post Wave 0 spike)
Target Review: Sprint 004 T001; before expanding view API
Owner: Unassigned
```

### Accepted Shortcut

`AnalysisDataView` exposes tuple columns and custom `column()` API instead of Polars LazyFrame payload.

### Reason

Backend-neutral contract (D-011); avoid locking domain to pandas/Polars in Sprint 003.

### Consequences

- custom mini-API that may grow toward DataFrame emulation,
- friction for resampling, join_asof, LazyFrame,
- Sprint 004 needs conversion boundary for Polars MTF path.

### Safe Operating Boundary

Do not extend `AnalysisDataView` with select/join/resample methods. New batch paths should use thin `MarketFrame` wrapper (future) per simplification review.

### Repayment Trigger

Sprint 004 spike confirms Polars resample/align; or second analytical backend requires shared columnar contract.

### Repayment Direction

Introduce `MarketFrame(pl.LazyFrame, metadata)` for batch paths; migrate components incrementally; deprecate view API growth not conversions at boundary.

### Related Tasks

- Sprint 004 Design Principles
- ADR-MA-012 (planned)

---

## TD-016 — ComponentId and ImplementationId Dual Identity Axis

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Analysis
Introduced: Sprint 003
Target Review: With TD-013 (second backend)
Owner: Unassigned
```

### Accepted Shortcut

Separate semantic component identity and implementation identity in public types and cache keys.

### Reason

Supports multiple backends and versioned implementations per vision architecture.

### Consequences

- two versioning dimensions for single NumPy implementation,
- longer identity keys and resolver tests.

### Safe Operating Boundary

One implementation per component in CI registry.

### Repayment Trigger

Second implementation of same component shipped.

### Repayment Direction

Collapse to single identity axis if interchange never needed; else keep and document in ADR.

---

# 6. Planned Debt Boundaries

The following shortcuts may be accepted later but are not yet introduced:

```text
- limited provider set,
- limited asset-class coverage,
- bar-only Market Data MVP,
- local-only research execution,
- no UI,
- no distributed task scheduler,
- no live multi-account support,
- no automatic ML model registry.
```

They should become technical-debt entries only when implementation consciously relies on them and repayment conditions are known.

---

# 7. Debt Review Rules

Review technical debt:

- at sprint retrospectives,
- before phase completion,
- before introducing related abstractions,
- when a repayment trigger occurs,
- when a debt item becomes a correctness risk.

A debt item must move to `PROBLEM_REGISTRY.md` or a bug when it begins violating expected behaviour or safety.

Do not use technical debt as a label for every unfinished feature.
