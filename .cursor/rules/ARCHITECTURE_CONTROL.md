# Architecture Control and Module Flow Rules

## 1. Purpose

This document defines mandatory controls for preserving architecture, module boundaries and data flow in the Trading Research Framework.

It complements:

- `ARCHITECTURE_FOUNDATIONS.md`
- `ARCHITECTURE_TECHNICAL.md`
- `WORKFLOWS_AI_ADR.md`
- module-level `AGENTS.md` files
- sprint and task definitions

The purpose is to prevent locally correct tasks from creating globally incorrect dependencies, duplicated responsibilities or undocumented cross-module flows.

---

## 2. Core Rule

An implementation task may change code only within approved architectural boundaries.

An agent must not create, reverse or expand dependencies between modules without explicit architectural approval.

Passing tests is not sufficient when the change violates domain ownership, dependency direction or workflow independence.

---

## 3. Domain Ownership

The following ownership rules are mandatory:

```text
Market
    owns trusted market facts, datasets and market-data contracts

Market Analysis
    owns reusable Features, Structures and States

Strategy
    owns Market Models, Signal Models, Exit Models, Risk Models,
    Strategy Models and SignalOccurrence

Research
    owns research orchestration, historical simulation,
    research datasets and analytics

Execution
    owns broker interaction, orders, fills, positions,
    reconciliation and operational execution controls
```

A module may consume public outputs of another module.

It must not take ownership of another module's responsibilities.

---

## 4. Dependency Direction

Allowed high-level direction:

```text
Market
  ↓
Market Analysis
  ↓
Strategy
  ├── Research
  └── Execution
```

Additional allowed consumption:

```text
Market → Research
Market → Execution
Market Analysis → Research
Market Analysis → Execution
```

Forbidden examples:

```text
Market → Research implementation
Market → Execution implementation
Strategy → Research
Execution → Research
src/ → concrete user_data modules
Domain → concrete infrastructure adapters
```

Infrastructure implements contracts defined by domain or application layers.

Domain and application code must not depend directly on provider SDKs, broker SDKs, storage drivers or framework-specific adapters.

---

## 5. Task Architecture Impact

Every implementation task must define:

```markdown
## Architecture Impact

Owning module:
- ...

Allowed dependencies:
- ...

Forbidden dependencies:
- ...

Public contracts changed:
- none / list

Persisted schemas changed:
- none / list

New cross-module flow:
- none / description

ADR required:
- yes / no

Architecture references:
- ...
```

A task is not ready for implementation when:

- the owning module is unclear,
- a new dependency direction is unresolved,
- a public contract change is not assessed,
- an architectural decision is still open.

---

## 6. Cross-Module Change Policy

### Changes within one module

The agent may implement independently when:

- ownership is clear,
- public contracts remain unchanged,
- no new cross-module dependency is introduced,
- the change matches existing architecture.

### Public contract changes

Before implementation, the agent must:

1. identify all consumers,
2. describe compatibility impact,
3. identify migration requirements,
4. determine whether documentation or ADR updates are required,
5. obtain explicit approval when the change is breaking or architectural.

### New cross-module flow

The agent must stop before implementation and report:

```text
source module
target module
data, command or event crossing the boundary
public contract used
dependency direction
reason the flow is required
alternatives considered
compatibility impact
```

### Ownership or workflow changes

Changes to:

- domain ownership,
- dependency direction,
- Signal Research flow,
- Strategy Research flow,
- Strategy Execution flow,
- dataset lifecycle,
- model composition semantics,

require an ADR and explicit approval.

---

## 7. Pull Request Architecture Review

Every task PR must include:

```markdown
## Architecture Review

- [ ] Owning domain is explicit
- [ ] Dependency direction is preserved
- [ ] No infrastructure implementation leaks into domain or application code
- [ ] No concrete `user_data` module is imported from `src`
- [ ] No responsibility is duplicated in another module
- [ ] No public contract changed silently
- [ ] Persisted schemas remain compatible or have a migration plan
- [ ] Workflow independence is preserved
- [ ] Any new cross-module flow is documented
- [ ] ADR was added where required
- [ ] Tests cover the architectural boundary where practical
```

A PR must not be merged only because linting and unit tests pass.

Architecture review is a separate acceptance condition.

---

## 8. Architecture Checks in CI

CI should include a dedicated architecture-check stage.

Minimum checks:

```text
market must not import research
market must not import execution
strategy must not import research
execution must not import research
domain modules must not import infrastructure implementations
src must not import concrete user_data modules
research and execution must remain independent
```

Recommended command:

```text
uv run pytest tests/architecture
```

Suggested location:

```text
tests/architecture/
├── test_dependency_direction.py
├── test_src_user_data_boundary.py
├── test_domain_infrastructure_boundary.py
└── test_workflow_independence.py
```

These tests should fail when a prohibited import or dependency is introduced.

---

## 9. Sprint Integration Review

Task PR review answers:

```text
Is this task implemented correctly?
```

The final sprint PR answers:

```text
Do all completed tasks together form a correct system capability?
```

Before merging a sprint branch into `main`, review:

- new module dependencies,
- new public contracts,
- data and control flow between modules,
- duplicated responsibilities,
- consistency between code and architecture documentation,
- integration tests for the complete vertical slice,
- compatibility of merged task contracts,
- whether temporary shortcuts became permanent dependencies,
- whether any god object or hidden orchestration appeared.

The final sprint PR must include an architecture integration summary.

---

## 10. Agent Stop Conditions

The agent must stop and request approval when:

- implementation requires a new module-to-module interaction,
- an existing dependency must be reversed,
- public contract semantics must change,
- persisted data or configuration schema must change,
- a responsibility does not have a clear owning domain,
- the task conflicts with architecture documentation,
- implementation would require speculative infrastructure,
- multiple modules would need coordinated redesign,
- an ADR is required but does not exist.

The agent must not silently resolve architectural ambiguity in code.

---

## 11. Prohibited Behaviours

The following are prohibited:

1. Introducing imports across forbidden module boundaries.
2. Calling infrastructure implementations directly from domain logic.
3. Accessing concrete `user_data` modules from `src`.
4. Moving responsibilities between domains without an ADR.
5. Combining Signal Research, Strategy Research and Strategy Execution into one pipeline.
6. Making Execution depend on Research datasets, rankings or reports.
7. Hiding cross-module communication inside utility modules.
8. Creating a generic manager that owns multiple domain workflows.
9. Changing public contracts without inspecting consumers.
10. Treating passing tests as proof of architectural correctness.
11. Expanding task scope to redesign adjacent modules without approval.
12. Creating temporary dependency shortcuts without recording them as technical debt.

---

## 12. Completion Checklist

Before completing a task:

```text
[ ] Owning module is correct
[ ] Allowed dependencies are respected
[ ] Forbidden dependencies were not introduced
[ ] Public contracts were inspected
[ ] Consumers were checked
[ ] src/user_data boundary is preserved
[ ] Domain/infrastructure boundary is preserved
[ ] Workflow independence is preserved
[ ] New cross-module flows were approved and documented
[ ] Architecture tests pass
[ ] Relevant documentation was updated
[ ] ADR exists where required
[ ] No unrelated architectural change was included
```

Before merging a sprint into `main`:

```text
[ ] Sprint goal is delivered as one coherent capability
[ ] Task contracts work together
[ ] Cross-module flow is explicit
[ ] Integration tests pass
[ ] Architecture checks pass
[ ] No duplicated responsibility exists
[ ] No hidden dependency or god object was introduced
[ ] Documentation matches the final implementation
[ ] Open architectural risks are recorded
```

---

## 13. Final Rule

```text
Agents may implement inside approved boundaries.

Agents must not design new boundaries implicitly.

Architecture changes require explicit review, documentation and approval.
```
