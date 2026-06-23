# AI Agent Instructions

Read this file before modifying the repository.

## Required Reading Order

1. `AGENTS.md` (this file)
2. `docs/planning/CURRENT_STATUS.md`
3. `docs/planning/ROADMAP.md`
4. `docs/architecture/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
5. `docs/architecture/ARCHITECTURE_TECHNICAL_UPDATED.md`
6. relevant module documentation under `docs/architecture/` and `docs/agents/`
7. relevant ADRs under `docs/adr/`
8. existing contracts and tests in `src/` and `tests/`

Do not implement from an issue description alone when repository contracts already exist.

## Architecture Rules

- preserve the `src/` and `user_data/` boundary,
- keep strategies stateless,
- keep business logic independent from external APIs,
- use adapters/interfaces for external systems,
- prefer composition over inheritance,
- avoid global mutable state,
- reject naive datetimes; use UTC internally,
- use `Clock` abstractions instead of `datetime.now()` in domain and application logic.

## Before Modifying Code

1. read relevant architecture and module documentation,
2. inspect existing contracts and tests,
3. keep changes within the requested task scope,
4. add tests for every behavioural change,
5. do not introduce speculative abstractions or infrastructure.

## Quality Commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Report failed checks. Do not hide or disable them.

## Module-Specific Agent Docs

- Market Data: `docs/agents/AGENTS_UPDATED.md`
- Multitimeframe Market Model: `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md`

## Planning

- sprint tasks: `docs/planning/sprints/`
- problems: `docs/planning/PROBLEM_REGISTRY.md`
- ideas: `docs/planning/IDEA_INBOX.md`
- technical debt: `docs/planning/TECHNICAL_DEBT.md`

## Sprint Git Workflow

- one integration branch per sprint: `sprint/<sprint-slug>` (for example `sprint/market-data-mvp`)
- one namespaced task branch per sprint task: `sprint/<sprint-slug>/<task-slug>`
- branch, PR and commit names describe the work — not sprint task IDs
- within a task: only logical commits; do not batch multiple tasks or split one task artificially by file
- mandatory path: task branch → commit → push → PR → review / CI → squash merge → delete branch
- the agent implements, pushes and opens the PR, then **stops before merge**

See `.cursor/rules/sprint-git-workflow.mdc`.

## Architecture Control

Before cross-module or contract-changing work, read `.cursor/rules/ARCHITECTURE_CONTROL.md`.

Every task PR must preserve domain ownership, dependency direction and the `src/` / `user_data/` boundary.

## Boundaries

- do not place credentials, datasets, research results or proprietary strategies in the repository,
- do not import `user_data/` from `src/trading_framework/`,
- do not add dependencies without a demonstrated need.
