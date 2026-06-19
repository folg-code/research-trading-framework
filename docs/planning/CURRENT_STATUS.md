# Trading Research Framework

# CURRENT_STATUS.md

## 1. Purpose

This document provides a concise snapshot of the current state of the Trading Research Framework.

It answers:

- where the project is now,
- what has been completed,
- what is actively being prepared,
- what is blocked,
- what decisions remain open,
- what capability should be built next.

This file is a status summary.

It is not the operational task board.

Detailed task state belongs in GitHub Issues and GitHub Projects once configured.

---

## 2. Status Metadata

```text
Status Date: 2026-06-19
Current Phase: Phase 0 — Project Governance
Current Milestone: Architecture and Planning Baseline
Implementation Status: Pre-implementation / architecture-first
Overall Status: IN_PROGRESS
```

---

## 3. Current Objective

Establish a consistent architectural and project-management baseline before implementation begins.

The immediate goal is:

```text
Create a repository-ready documentation set
that can guide human and AI-assisted implementation
without contradictory domain or workflow assumptions.
```

---

## 4. Completed Capabilities

### Architectural Foundations

The following are defined:

- five primary domains:
  - Market,
  - Market Analysis,
  - Strategy,
  - Research,
  - Execution;
- three independent system capabilities:
  - Signal Research,
  - Strategy Research,
  - Strategy Execution;
- modular-monolith direction;
- `src/` and `user_data/` separation;
- domain ownership and dependency direction;
- reproducibility and lineage principles;
- no-god-object rule;
- controlled technology adoption.

### Market Analysis Architecture

The following decisions are established:

```text
Market Analysis Components
├── Features
├── Structures
└── States
```

Also defined:

- Market Analysis Engine,
- explicit component dependencies,
- DAG-based computation,
- lazy execution,
- shared-node reuse,
- component cache identity,
- local component lifecycle,
- working implementation fingerprints,
- controlled component promotion.

### Model Composition

The following model semantics are established:

```text
Market Model
=
declarative expression over Market Analysis outputs
```

```text
Signal Model
=
declarative expression over Market Analysis outputs
```

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

Also established:

- `SignalOccurrence` belongs to the Strategy Domain,
- position sizing belongs to the Risk Model in Version 1,
- models cannot access arbitrary DataFrames,
- simple source fields may use controlled `MarketFieldReference`.

### Research Architecture

The following are established:

- Research Computation is separate from Research Analytics,
- Signal Research supports:
  - Market Model only,
  - Signal Model only,
  - Market Model × Signal Model;
- Strategy Research evaluates complete Strategy Models,
- batch/vectorized backtesting belongs to Research,
- rankings are not proof of robustness,
- multiple-testing metadata is required for large spaces,
- stored Research Datasets should be reused.

### Strategy Execution Architecture

The following modes are separated from batch Research:

```text
Replay Execution
Paper Execution
Live Execution
```

Also established:

- Strategy Execution does not consume Research workflow state,
- operational risk controls are separate from Strategy Risk Models,
- orders, fills, positions, reconciliation and recovery belong to Execution.

### Market Data Architecture

The following are established:

- provider-independent market facts,
- explicit dataset identity and lineage,
- Parquet as primary historical analytical storage,
- dataset lifecycle:
  ```text
  WORKING → FINALIZED → PUBLISHED
  ```
- finalization and publication are separate,
- Research consumes published `DatasetRef` versions,
- no hidden Research downloads,
- futures contracts preserve actual contract identity,
- continuous futures are lineage-aware derived datasets,
- raw retention is policy-driven.

### Project Management Architecture

The following are defined:

- planning hierarchy,
- one-week sprint default,
- Definition of Ready,
- Definition of Done,
- work statuses,
- vertical-slice principle,
- GitHub Issues and Projects as future operational source of truth,
- roadmap phases,
- local component promotion lifecycle.

---

## 5. Documentation Baseline

Prepared or updated architecture documents include:

```text
ARCHITECTURE_FOUNDATIONS.md
ARCHITECTURE_TECHNICAL.md
WORKFLOWS_AI_ADR.md
MARKET_ANALYSIS_AND_MODEL_COMPOSITION.md
MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md
DATA_MODULE.md
AGENTS.md
AGENTS_MULTITIMEFRAME_MARKET_MODEL.md
PROJECT_MANAGEMENT.md
```

Planning documents being established:

```text
ROADMAP.md
CURRENT_STATUS.md
PROBLEM_REGISTRY.md
IDEA_INBOX.md
TECHNICAL_DEBT.md
```

---

## 6. Work in Progress

### Phase 0 — Project Governance

Current work:

- complete the planning document set,
- define initial problems and ideas,
- distinguish known problems from accepted debt,
- prepare the repository governance structure,
- prepare the first implementation sprint.

### Documentation Consistency

Remaining consistency work should include:

- final naming and numbering review across all documents,
- removal of residual outdated terminology,
- validation of directory examples,
- validation of cross-document references,
- conversion of accepted architectural decisions into individual ADR files.

---

## 7. Blocked Work

No implementation work is technically blocked.

However, repository implementation should not begin before the following minimum governance tasks are completed:

```text
ROADMAP.md
CURRENT_STATUS.md
PROBLEM_REGISTRY.md
IDEA_INBOX.md
TECHNICAL_DEBT.md
initial ADR list
Sprint 001 definition
```

The project is intentionally architecture-first at this stage.

---

## 8. Open Critical Problems

Current high-priority problems include:

1. Exact canonical numeric types for price, volume and quantity are not yet fixed.
2. Dataset logical identity and version-generation algorithm need implementation-level definition.
3. Component and model fingerprint algorithms need specification.
4. Public component discovery from `user_data/` needs a safe contract.
5. Market Analysis result storage schemas are not yet fixed.
6. Research Dataset physical schemas remain intentionally undefined.
7. Trading Calendar implementation or adapter choice is not selected.
8. Vectorized backtest simulation semantics need explicit initial limits.
9. Research/runtime parity criteria need formal definition.
10. Initial repository package names and import boundaries need implementation validation.

Detailed entries belong in `PROBLEM_REGISTRY.md`.

---

## 9. Open Architectural Decisions

The architecture has many accepted conceptual decisions, but individual ADR files still need to be created.

Initial ADR candidates:

```text
ADR-0001 Modular Monolith
ADR-0002 Separate src and user_data
ADR-0003 UTC Internal Time
ADR-0004 Independent Research and Execution Workflows
ADR-0005 Market Analysis Domain and Taxonomy
ADR-0006 Declarative Market and Signal Models
ADR-0007 Dataset Lifecycle and Publication
ADR-0008 Parquet Historical Storage
ADR-0009 Batch Backtest vs Replay Execution
ADR-0010 Working Component and Model Fingerprints
```

These decisions are already described in architecture documents.

The missing work is to preserve their individual historical rationale.

---

## 10. Known Risks

### Architecture Drift

Multiple documents may diverge unless changes update the complete affected documentation set.

### Over-Design Before Implementation

Some contracts may prove too detailed or incorrectly shaped after the first vertical slices.

### Premature Taxonomy

Permanent module directories may be introduced before component volume justifies them.

### Temporal Correctness

Multitimeframe and session logic can introduce look-ahead bias if implementation deviates from `available_at` semantics.

### Research-Space Explosion

Independent parameters, models and timeframes can create excessive candidate counts and false discoveries.

### Reproducibility Cost

Fingerprinting, dataset identity and lineage may become too heavy if their minimum viable implementation is not carefully scoped.

### Public/Private Boundary Leakage

Proprietary model logic may accidentally move into framework code.

### Infrastructure Creep

Provider, database, messaging and deployment technologies may be introduced before a demonstrated requirement.

---

## 11. Next Planned Capability

The next planned implementation capability should be:

```text
Phase 1 — Repository Foundation
```

Recommended first implementation milestone:

```text
Installable package with:
- src/user_data separation,
- core identifiers,
- UTC time primitives,
- validated configuration,
- unit-test structure,
- Ruff,
- mypy,
- pytest,
- CI.
```

This should precede Market Data implementation.

---

## 12. Recommended Sprint 001 Goal

```text
Create a repository foundation that installs,
passes CI and enforces the primary architectural boundaries.
```

Suggested deliverables:

- repository directory structure,
- `pyproject.toml`,
- package initialization,
- `user_data/` placeholder structure,
- pytest configuration,
- Ruff configuration,
- mypy configuration,
- GitHub Actions CI,
- core identifiers,
- timezone-aware timestamp helpers or value objects,
- architecture validation tests where practical,
- AI-agent entry instructions.

Out of scope:

- provider implementations,
- Parquet repository,
- Market Analysis Engine,
- model research,
- execution.

---

## 13. Status Update Rules

Update this document when:

- a sprint begins or ends,
- the current phase changes,
- a capability is completed,
- a critical blocker appears,
- an architectural decision materially changes direction,
- the next planned capability changes.

Do not use this file as a second task board.

Keep it concise enough to understand project state quickly.
