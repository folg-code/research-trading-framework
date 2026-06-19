# Trading Research Framework

# PROJECT_MANAGEMENT.md

## 1. Purpose

This document defines how development of the Trading Research Framework is planned, tracked and reviewed iteratively.

It complements the architectural documentation, but does not replace it.

Architecture documents define:

- what the system is,
- domain boundaries,
- technical rules,
- workflow contracts,
- AI implementation rules,
- architectural decisions.

This document defines:

- what is being built now,
- what is planned next,
- how progress is measured,
- how work is prioritised,
- how problems and ideas are recorded,
- how sprints and tasks are managed,
- how the roadmap evolves based on new knowledge.

The project management process must remain lightweight, explicit and useful for both human maintainers and AI coding agents.

---

## 2. Planning Hierarchy

The framework uses the following planning hierarchy:

```text
Vision
  ↓
Roadmap
  ↓
Milestones / Epics
  ↓
Sprint
  ↓
Tasks
```

Supporting registers:

```text
Idea Inbox
Problem Registry
Technical Debt
Architectural Decision Records
Progress Log
```

Each level has a different purpose and must not be mixed with the others.

---

## 3. Vision

The project vision is defined in the architectural foundation documents.

The roadmap must reference that vision rather than duplicate it.

The vision describes the long-term system direction.

It must not be used as a detailed task list.

---

## 4. Roadmap

The roadmap describes major development phases and capabilities.

It should remain directional and should not contain detailed task breakdowns for distant phases.

Suggested roadmap structure:

```text
Phase 0 — Project Governance
Phase 1 — Repository Foundation
Phase 2 — Market Data MVP
Phase 3 — Market Analysis Engine MVP
Phase 4 — Market Analysis Components and Multitimeframe
Phase 5 — Signal Research MVP
Phase 6 — Strategy Research MVP
Phase 7 — Robustness Research
Phase 8 — Strategy Execution: Replay and Paper
Phase 9 — Live and Multi-Account
```

Each roadmap phase should define:

- purpose,
- expected capability,
- scope,
- completion criteria,
- dependencies,
- risks,
- out-of-scope items.

The roadmap should not be tied rigidly to dates unless a real delivery deadline exists.

The project is research-heavy and architectural assumptions may change after implementation feedback.

---

## 5. Roadmap Phases

## 5.1 Phase 0 — Project Governance

Purpose:

- define the planning process,
- create roadmap and status tracking,
- establish issue and PR workflows,
- establish sprint planning,
- establish ADR review rules.

Expected outputs:

- `PROJECT_MANAGEMENT.md`,
- `ROADMAP.md`,
- `CURRENT_STATUS.md`,
- `PROBLEM_REGISTRY.md`,
- `IDEA_INBOX.md`,
- sprint templates,
- issue templates,
- GitHub Project configuration.

---

## 5.2 Phase 1 — Repository Foundation

Purpose:

- create the implementation foundation required by all modules.

Expected capabilities:

- package structure,
- test structure,
- CI,
- linting,
- formatting,
- type checking,
- core identifiers,
- time primitives,
- basic configuration loading.

---

## 5.3 Phase 2 — Market Data MVP

Purpose:

- provide the first complete market data vertical slice.

Expected flow:

```text
External File
    ↓
Inspect
    ↓
Normalize
    ↓
Validate
    ↓
Store in Parquet
    ↓
Register Dataset Version
    ↓
Query Through Repository
```

Expected capabilities:

- canonical market models,
- dataset identity and lifecycle,
- separate finalization and publication,
- external file import,
- UTC normalization,
- validation,
- Parquet persistence,
- dataset registry,
- historical query.

---

## 5.4 Phase 3 — Market Analysis Engine MVP

Purpose:

- calculate reusable analytical components through explicit dependencies.

Expected capabilities:

- Market Analysis component contracts,
- Component Registry,
- dependency graph,
- cycle detection,
- cache identity,
- lazy execution,
- one complete Feature, Structure or State vertical slice.

---

## 5.5 Phase 4 — Market Analysis Components and Multitimeframe

Purpose:

- support safe timeframe-aware analytical requests.

Expected capabilities:

- explicit resampling nodes,
- source, computation and evaluation timeframe distinction,
- `available_at` semantics,
- last-closed-bar alignment,
- backward as-of alignment,
- Market Analysis components,
- Market Model expression evaluation.

---

## 5.6 Phase 5 — Signal Research MVP

Purpose:

- evaluate Market Models and Signal Models without requiring complete strategies.

Expected capabilities:

- explicit Signal Research scope:
  - Market Model only,
  - Signal Model only,
  - Market Model × Signal Model,
- Signal Model contract,
- Market Model contract,
- one-condition model support,
- reusable SignalOccurrences,
- forward-return dataset,
- MFE and MAE analysis,
- persistent Signal Research Dataset,
- basic reusable analytics.

---

## 5.7 Phase 6 — Strategy Research MVP

Purpose:

- evaluate complete Strategy Models.

Expected capabilities:

- Exit Model contract,
- Risk Model contract,
- Strategy composition,
- basic backtest engine,
- trade-level results,
- execution assumptions,
- persistent Strategy Research Dataset.

---

## 5.8 Phase 7 — Robustness Research

Purpose:

- evaluate candidate stability rather than only rank raw performance.

Expected capabilities:

- walk-forward analysis,
- Monte Carlo analysis,
- parameter sensitivity,
- family analysis,
- multiple-testing metadata,
- out-of-sample validation,
- complexity-aware analytics.

---

## 5.9 Phase 8 — Strategy Execution: Replay and Paper

Purpose:

- validate Strategy Models in runtime-like conditions.

Expected capabilities:

- replay feed,
- Replay Clock,
- Replay Execution,
- Paper Execution,
- order lifecycle,
- fills,
- positions,
- reconciliation,
- execution risk controls.

---

## 5.10 Phase 9 — Live and Multi-Account

Purpose:

- support operational live execution and account scaling.

Expected capabilities:

- broker adapters,
- persistent execution records,
- monitoring,
- alerts,
- recovery,
- multi-account coordination,
- operational controls.

Detailed planning for this phase must remain deferred until previous phases validate the required abstractions.

---

## 6. Milestones and Epics

A roadmap phase is divided into milestones and epics.

A milestone represents a meaningful system capability.

An epic groups related work required to deliver that capability.

Example:

```text
Milestone: Market Data MVP

Epic 1: Canonical market models
Epic 2: Dataset identity and lifecycle
Epic 3: External file import
Epic 4: Validation
Epic 5: Parquet persistence
Epic 6: Historical querying
```

Epics should describe a result or capability rather than only a technical layer.

Preferred:

```text
Import and publish a validated OHLCV dataset
```

Avoid:

```text
Implement repositories
```

Repositories may be part of an implementation, but they are not the user-visible or system-level outcome.

---

## 7. Sprint Model

The default sprint duration is:

```text
1 week
```

Short sprints are preferred because:

- the project is exploratory,
- architectural feedback appears quickly,
- AI-assisted development increases implementation speed,
- two-week plans may become obsolete before completion.

Each sprint must have:

- one main Sprint Goal,
- a limited number of related deliverables,
- explicit scope,
- explicit out-of-scope items,
- acceptance criteria,
- known dependencies,
- known risks,
- end-of-sprint review,
- retrospective notes.

A sprint must not become a random collection of unrelated tasks.

Example:

```text
Sprint Goal:
Framework can import, validate and publish one OHLCV dataset.

Deliverables:
- Instrument and MarketBar models
- DatasetId, DatasetRef and DatasetMetadata
- CSV importer
- UTC timestamp normalization
- OHLCV validation
- Parquet writer
- unit and integration tests
```

---

## 8. Task Model

A task must be small enough to:

- implement,
- test,
- review,
- document,
- complete in one focused PR or one logical part of a PR.

Suggested task template:

```markdown
# Task: Implement DatasetRef

## Context

Why this task is needed.

## Scope

What must be implemented.

## Out of Scope

What must not be implemented.

## Architecture References

- ARCHITECTURE_FOUNDATIONS.md
- ARCHITECTURE_TECHNICAL.md
- relevant module documentation
- relevant ADRs

## Acceptance Criteria

- [ ] DatasetRef contains dataset_id and version
- [ ] Object is immutable
- [ ] Equality and hashing work correctly
- [ ] Invalid versions are rejected
- [ ] Unit tests exist
- [ ] Public exports are updated

## Test Cases

- ...
```

Tasks should not contain unresolved architectural questions.

When a task depends on an architectural decision, the decision must be resolved through design work or an ADR first.

---

## 9. Work Categories

The project distinguishes the following work categories:

```text
Epic
Feature
Bug
Research
Architecture
Technical Debt
Documentation
Maintenance
```

### Feature

Introduces a defined system capability.

### Bug

Corrects behaviour that violates an existing contract or expected result.

### Research

Investigates an unresolved problem or validates a technical assumption.

A research task may end with:

- recommendation,
- prototype,
- rejected approach,
- ADR proposal,
- implementation task.

It does not need to end with production code.

### Architecture

Changes or defines domain boundaries, contracts, dependency direction or major implementation principles.

Material architectural work normally requires an ADR.

### Technical Debt

Represents a known implementation weakness that does not currently break expected behaviour but increases future cost or risk.

---

## 10. Idea Inbox

The Idea Inbox stores unvalidated ideas.

Examples:

```text
- visual DAG editor
- ML-based feature selection
- options gamma snapshots
- distributed research workers
- remote component registry
```

An idea does not yet require:

- implementation,
- priority,
- acceptance criteria,
- sprint assignment.

An idea must not automatically become a backlog task.

Before promotion into the backlog, it should be assessed for:

- value,
- fit with the project vision,
- architectural impact,
- dependency impact,
- implementation cost,
- current necessity.

Possible idea statuses:

```text
INBOX
UNDER_REVIEW
PROMOTED
DEFERRED
REJECTED
```

---

## 11. Problem Registry

The Problem Registry stores observed architectural, research and implementation problems.

Examples:

```text
- higher-timeframe alignment may introduce look-ahead
- full Cartesian expansion creates excessive candidate count
- live recorder may produce excessive small files
- dataset version identity is not yet fully defined
```

Each problem should contain:

```text
ID
Title
Description
Evidence
Impact
Affected modules
Current status
Possible directions
Related ADRs
Related tasks
Owner
```

A problem may later produce:

- a research task,
- a bug,
- an epic,
- a technical-debt item,
- an ADR.

The registry should preserve unresolved issues even when they are not currently prioritised.

---

## 12. Backlog Rules

The Product and Engineering Backlog contains only items that are sufficiently understood to be considered for implementation.

An item should enter the backlog only when:

- its purpose is understood,
- its owning domain is known,
- its scope can be described,
- its value or necessity is visible,
- major dependencies are known,
- it is not merely an unvalidated idea.

The backlog must not become a storage location for every possible future feature.

There must be one operational source of truth for task state.

Recommended source of truth:

```text
GitHub Issues + GitHub Projects
```

Markdown documents should store:

- planning rules,
- roadmap,
- sprint plans and retrospectives,
- project status,
- problem and idea registers.

Task progress should not be maintained independently in both Markdown and GitHub Issues.

---

## 13. Work Statuses

Supported statuses:

```text
INBOX
READY
PLANNED
IN_PROGRESS
BLOCKED
IN_REVIEW
DONE
DEFERRED
REJECTED
```

### INBOX

New idea, problem or unprocessed request.

### READY

The item is sufficiently specified and meets Definition of Ready.

### PLANNED

The item is assigned to a milestone or sprint.

### IN_PROGRESS

Implementation or research has started.

### BLOCKED

Progress cannot continue due to an explicit dependency or unresolved issue.

Every blocked item must record:

- blocker,
- owner or dependency,
- required resolution.

### IN_REVIEW

The implementation, design or ADR is awaiting review.

### DONE

The item satisfies Definition of Done.

### DEFERRED

The item remains valid but is consciously postponed.

### REJECTED

The item will not be implemented.

The rejection reason should be recorded.

---

## 14. Definition of Ready

A task may enter a sprint only when:

```text
[ ] Goal is clear
[ ] Scope is explicit
[ ] Out-of-scope items are explicit
[ ] Acceptance criteria exist
[ ] Owning domain is identified
[ ] Relevant architecture documents are referenced
[ ] Dependencies are known
[ ] Task is sufficiently small
[ ] Required inputs are available
[ ] No unresolved architectural decision blocks implementation
[ ] Expected tests are identified
```

An item that does not meet Definition of Ready remains in the backlog or becomes a research/design task.

---

## 15. Definition of Done

A task is complete only when:

```text
[ ] Requested behaviour is implemented
[ ] Acceptance criteria are satisfied
[ ] Unit tests pass
[ ] Integration tests exist where infrastructure changed
[ ] Regression tests exist for bug fixes
[ ] Linting passes
[ ] Formatting passes
[ ] Type checking passes
[ ] Relevant documentation is updated
[ ] ADR is added or updated when required
[ ] Public contracts remain consistent
[ ] src/user_data boundary is preserved
[ ] No hidden breaking change was introduced
[ ] Errors are handled explicitly
[ ] PR was reviewed
[ ] Task and project status were updated
```

Passing tests alone does not mean the task is done if documentation, lineage or architecture contracts are incomplete.

---

## 16. Iterative Development Cycle

The standard project cycle is:

```text
1. Capture
2. Clarify
3. Prioritise
4. Plan
5. Implement
6. Review
7. Validate
8. Learn
9. Update Roadmap
```

## 16.1 Capture

Record a new:

- idea,
- problem,
- requirement,
- bug,
- technical-debt item.

Do not immediately commit to implementation.

## 16.2 Clarify

Determine:

- what type of item it is,
- which domain owns it,
- what evidence exists,
- whether it requires an ADR,
- whether it is currently needed.

## 16.3 Prioritise

Assess:

```text
Value
Architectural Importance
Dependency Enablement
Risk Reduction
Urgency
Implementation Cost
```

A simple priority score may be used:

```text
Priority Score
=
Value
+ Risk Reduction
+ Dependency Enablement
- Estimated Cost
```

The score supports discussion but does not replace judgement.

## 16.4 Plan

Select a small sprint scope and define one Sprint Goal.

Do not fill a sprint only to maximise utilisation.

## 16.5 Implement

Prefer:

- focused branches,
- small PRs,
- tests with implementation,
- architecture references in task descriptions.

## 16.6 Review

Review must assess:

- correctness,
- architecture compliance,
- scope compliance,
- tests,
- maintainability,
- unnecessary abstraction,
- hidden breaking changes.

## 16.7 Validate

Verify Definition of Done.

## 16.8 Learn

At sprint end, record:

- completed work,
- incomplete work,
- new problems,
- invalid assumptions,
- technical debt introduced,
- decisions required,
- process improvements.

## 16.9 Update Roadmap

The roadmap must change when implementation provides new evidence.

The roadmap is a planning model, not an immutable commitment.

---

## 17. Sprint Review and Retrospective

Every sprint should end with a combined review and retrospective.

Suggested structure:

```markdown
# Sprint Review

## Sprint Goal

...

## Completed

- ...

## Not Completed

- ...

## Demonstrated Capability

- ...

## Problems Discovered

- ...

## Architectural Decisions Required

- ...

## Technical Debt Added

- ...

## Lessons Learned

- ...

## Changes to Roadmap or Backlog

- ...

## Next Recommended Sprint Goal

- ...
```

Sprint documents should preserve historical truth.

After sprint completion, do not rewrite the original plan to make it appear accurate.

Add the actual outcome and retrospective instead.

---

## 18. Local Component Development Lifecycle

Market Analysis components may move through:

```text
Local Working
    ↓
Experimental
    ↓
Candidate
    ↓
Promoted Framework Component
    ↓
Released Framework Component
```

Planning rules:

- local working development does not require formal public versioning,
- research use requires an implementation fingerprint,
- candidate promotion is an explicit task or PR,
- promotion is never automatic,
- proprietary components may remain local permanently,
- mutable model definitions used in research require definition fingerprints.

Suggested planning labels:

```text
lifecycle:working
lifecycle:candidate
lifecycle:framework
needs:promotion-review
```

---

## 19. Vertical Slice Principle

Development should progress through small complete capabilities rather than broad horizontal layers.

Example Market Data progression:

```text
Vertical Slice 1
External OHLCV file
→ normalization
→ validation
→ Parquet
→ DatasetRef
→ query

Vertical Slice 2
Missing range detection
→ provider synchronization
→ new DatasetRef

Vertical Slice 3
Live stream
→ recorder
→ finalization
→ publication

Vertical Slice 4
Futures contracts
→ contract metadata
→ continuous futures
```

Each slice should:

- provide an observable capability,
- validate architecture assumptions,
- produce tests,
- expose integration problems early,
- reduce speculative design.

The project must not attempt to fully design every future module before implementing the first usable flow.

---

## 20. Detailed Planning Horizon

Detailed task planning should cover only:

```text
Current phase
Next phase
```

Later phases should remain at roadmap or milestone level.

This prevents overplanning based on assumptions that may be invalidated by early implementation.

Before beginning a new phase:

- review lessons from the previous phase,
- update dependencies,
- update risks,
- refine the next milestone,
- reject obsolete tasks.

---

## 21. Progress Monitoring

Progress must be tracked by completed capabilities, not only by task count.

Recommended measures:

```text
Completed milestones
Completed vertical slices
Sprint Goal success rate
Blocked items
Open architectural decisions
Open critical problems
Test coverage of critical contracts
Number of deferred or rejected assumptions
Current phase completion
```

Avoid misleading metrics such as:

- lines of code,
- number of commits,
- number of generated files,
- number of completed trivial tasks.

`CURRENT_STATUS.md` should provide a concise current state.

Suggested content:

```text
Current Phase
Current Milestone
Current Sprint
Sprint Goal
Completed Capabilities
Work In Progress
Blocked Work
Open Critical Problems
Open ADRs
Known Risks
Next Planned Capability
```

---

## 22. GitHub Workflow

Recommended operational tooling:

```text
GitHub Issues
GitHub Projects
GitHub Milestones
Pull Requests
GitHub Actions
```

Responsibility split:

```text
ROADMAP.md
    strategic direction

GitHub Milestones
    phase and milestone tracking

GitHub Issues
    epics, tasks, bugs, research and problems

GitHub Project
    workflow status and current sprint

Sprint files
    plan, review and retrospective

ADRs
    architectural decision history
```

---

## 23. Recommended Labels

### Type

```text
type:epic
type:feature
type:bug
type:research
type:architecture
type:technical-debt
type:documentation
type:maintenance
```

### Domain

```text
domain:core
domain:time
domain:market
domain:market-analysis
domain:strategy
domain:research
domain:execution
domain:infrastructure
```

### Priority

```text
priority:critical
priority:high
priority:medium
priority:low
```

### State or Need

```text
status:blocked
needs:adr
needs:design
needs:research
needs:review
good-first-task
lifecycle:working
lifecycle:candidate
needs:promotion-review
```

Labels should remain limited and consistent.

Do not create overlapping labels with unclear meaning.

---

## 24. Pull Request Rules

A Pull Request should normally represent one coherent change.

Each PR should include:

```text
Purpose
Scope
Architecture references
Related issue
Main implementation decisions
Tests added or changed
Known limitations
Follow-up work
```

A PR must not silently include unrelated refactoring.

Large refactors should be separated from feature changes unless separation is impossible.

A PR affecting public contracts, domain boundaries or persisted data may require an ADR and migration notes.

---

## 25. AI Agent Planning Rules

Before implementing a task, an AI agent must inspect:

- current sprint,
- task scope,
- architecture references,
- relevant ADRs,
- current module contracts,
- existing tests.

An AI agent must not:

- promote an Idea Inbox item into implementation without approval,
- expand task scope silently,
- close a task without satisfying acceptance criteria,
- mark incomplete work as done,
- create speculative infrastructure,
- rewrite sprint history,
- modify the roadmap merely to match completed work,
- hide blockers or failed tests.

When a new problem is discovered, the agent should:

1. complete the current safe scope where possible,
2. record the problem,
3. describe its impact,
4. create or propose a follow-up issue,
5. avoid unrelated redesign unless the task cannot be completed safely.

---

## 26. Suggested Planning Directory

```text
docs/
├── architecture/
├── adr/
├── planning/
│   ├── PROJECT_MANAGEMENT.md
│   ├── ROADMAP.md
│   ├── CURRENT_STATUS.md
│   ├── PROBLEM_REGISTRY.md
│   ├── IDEA_INBOX.md
│   ├── TECHNICAL_DEBT.md
│   └── sprints/
│       ├── SPRINT_001.md
│       ├── SPRINT_002.md
│       └── ...
```

`PROJECT_MANAGEMENT.md` contains stable process rules.

`ROADMAP.md` contains strategic development phases.

`CURRENT_STATUS.md` contains the current project state.

`PROBLEM_REGISTRY.md` contains observed unresolved problems.

`IDEA_INBOX.md` contains unvalidated ideas.

`TECHNICAL_DEBT.md` contains accepted implementation debt.

Sprint documents preserve the plan and actual result of each sprint.

---

## 27. Initial Project Management Implementation

The first governance increment should include:

```text
1. Create PROJECT_MANAGEMENT.md
2. Create ROADMAP.md
3. Create CURRENT_STATUS.md
4. Create IDEA_INBOX.md
5. Create PROBLEM_REGISTRY.md
6. Create sprint template
7. Create issue templates
8. Configure GitHub labels
9. Configure GitHub Project statuses
10. Define Sprint 001
```

Do not attempt to create detailed issues for every future roadmap phase.

The initial detailed backlog should focus on:

```text
Phase 0 — Project Governance
Phase 1 — Repository Foundation
Phase 2 — Market Data MVP
```

---

## 28. Final Management Rules

1. Architecture and project planning are separate concerns.
2. The roadmap describes direction, not every task.
3. Detailed planning covers only the current and next phase.
4. Work is delivered through small vertical slices.
5. Every sprint has one clear goal.
6. Tasks require explicit scope and acceptance criteria.
7. Ideas do not automatically become backlog items.
8. Problems are recorded even when not immediately solved.
9. ADRs preserve architectural reasoning.
10. Progress is measured through delivered capabilities.
11. Sprint history is not rewritten.
12. The roadmap is updated when new evidence appears.
13. GitHub Issues and Projects are the operational source of truth.
14. Markdown stores stable rules, roadmap context and historical summaries.
15. AI agents must preserve scope, status truth and architectural contracts.
16. Market Analysis component promotion is explicit and never automatic.
17. Working components and mutable model definitions used in research require fingerprints.
18. Signal Research planning must identify its explicit scope.
19. Batch backtesting and Replay Execution are planned as different capabilities.

---

## 29. Final Statement

Development of the Trading Research Framework must be iterative, evidence-driven and capability-oriented.

The intended management flow is:

```text
Vision
  ↓
Roadmap
  ↓
Milestone
  ↓
Sprint Goal
  ↓
Small Vertical Slice
  ↓
Review and Validation
  ↓
Lessons Learned
  ↓
Updated Roadmap
```

The objective is not to predict the complete implementation path in advance.

The objective is to maintain clear direction, visible progress, controlled scope and a reliable record of problems, ideas and decisions while the architecture evolves through implementation.
