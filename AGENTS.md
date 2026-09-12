# AI Agent Instructions

Read this file before modifying the repository.

## Context Routing

Read this file first. Then start from the active task, PRD or sprint plan and
follow its links. If no active artifact identifies the context, use the short
entry points below. Read only the affected module, workflow, ADR and source
contracts; do not load the whole roadmap or vision for an ordinary code change.

| Area | Entry point |
|---|---|
| Product | `docs/vision/README.md` for future direction; `docs/product/` for PRDs |
| Architecture | `docs/reference/system/SYSTEM_OVERVIEW.md` |
| Modules | `docs/reference/system/MODULE_MAP.md` → affected page in `docs/reference/modules/` |
| Current work | `docs/planning/CURRENT_STATUS.md` → active sprint |
| Planning | `docs/planning/ROADMAP.md` and `docs/planning/README.md` |
| Engineering | `docs/onboarding/DEVELOPER_GUIDE.md` |
| Operations | `docs/reference/runbooks/README.md` |
| Reference | `docs/reference/README.md` |
| User documentation | `README.md` and `docs/reference/modules/` authoring guides |

Before implementing, inspect existing contracts and tests in `src/` and
`tests/`; an issue description alone is not a contract. For architecture or
contract changes, read the affected ADRs and relevant future-direction docs.

## Documentation

Single index: **`docs/README.md`** (taxonomy, paths, folder layout).

**Humans:** follow reading paths in `docs/README.md`.  
**Agents:** use the task and context-routing table above; open deep references only as needed.

After each merged wave: update `docs/reference/system/MODULE_MAP.md` and `docs/reference/system/SYSTEM_OVERVIEW.md` if paths changed. After contract changes: update `docs/reference/` and `docs/vision/` as needed in the same PR.

## Architecture Rules

- preserve the `src/` and `user_data/` boundary,
- treat `apps/*` as separate deployable consumers (ADR-0022); they must not import research/execution engines or provider/importer adapters,
- put ephemeral logs under `scratch/` (not root `.tmp_*`); generated demos under `artifacts/demo/`,
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

- Market Data: `docs/agents/AGENTS.md`
- Multitimeframe Market Model: `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL.md`

## Planning

- current sprint tasks: `docs/planning/sprints/`; completed records: `docs/archive/phases/`
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

The branch/PR path above is the project-level delivery rule.

## Architecture Control

Before cross-module or contract-changing work, read the relevant
`docs/reference/system/DEPENDENCY_RULES.md`, domain model and ADRs.

Every task PR must preserve domain ownership, dependency direction and the `src/` / `user_data/` boundary.

## Boundaries

- do not place credentials, datasets, research results or proprietary strategies in the repository,
- do not import `user_data/` from `src/trading_framework/`,
- do not add dependencies without a demonstrated need,
- do not delete or rewrite user data without explicit approval,
- do not expose credentials in logs, output or examples.
