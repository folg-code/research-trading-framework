# AI Agent Instructions

Read this file before modifying the repository.

## Required Reading Order

1. `AGENTS.md` (this file)
2. `docs/planning/CURRENT_STATUS.md`
3. `docs/planning/ROADMAP.md`
4. `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
5. `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md`
6. relevant docs under `docs/reference/` and `docs/agents/`
7. relevant ADRs under `docs/adr/`
8. existing contracts and tests in `src/` and `tests/`

Do not implement from an issue description alone when repository contracts already exist.

## Documentation

Single index: **`docs/README.md`** (taxonomy, paths, folder layout).

**Humans:** follow reading paths in `docs/README.md`.  
**Agents:** required reading order below + deep references as needed.

After each merged wave: update `docs/reference/MODULE_MAP.md` and `docs/reference/DATA_WORKFLOWS.md` if paths changed. After contract changes: update `docs/reference/` and `docs/vision/` as needed in the same PR.

## Architecture Rules

- preserve the `src/` and `user_data/` boundary,
- treat `apps/*` as separate deployable consumers (ADR-0022); they must not import research/execution engines or provider/importer adapters,
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

- one integration branch per sprint: `sprint/<sprint-slug>` (for example `sprint/market-analysis-mvp`)
- working branches use separate prefixes: `feat/`, `fix/`, `docs/`, `test/`, `refactor/` — not `sprint/<sprint-slug>/<task>`
- one PR per coherent, reviewable outcome into the sprint branch — not into `main`
- target PR size: 100–400 meaningful lines; split if larger than ~600–800
- branch, PR and commit names describe the work — not sprint task IDs
- sprint docs define **what** to deliver; they do not mandate PR boundaries
- mandatory path: working branch → commit → push → PR to sprint branch → review / CI → squash merge → delete branch
- when the sprint is complete: one final PR from `sprint/<sprint-slug>` to `main`
- the agent implements, pushes and opens the PR, then **stops before merge**

See `.cursor/rules/sprint-git-workflow.mdc`.

## Architecture Control

Before cross-module or contract-changing work, read `.cursor/rules/ARCHITECTURE_CONTROL.md`.

Every task PR must preserve domain ownership, dependency direction and the `src/` / `user_data/` boundary.

## Boundaries

- do not place credentials, datasets, research results or proprietary strategies in the repository,
- do not import `user_data/` from `src/trading_framework/`,
- do not add dependencies without a demonstrated need.
