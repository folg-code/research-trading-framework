# Developer Guide

Day-one setup. Documentation index: **[../README.md](../README.md)**.

AI agents: `AGENTS.md` at the repository root.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install and Quality Checks

```bash
uv sync --locked --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## Repository Layout

```text
src/trading_framework/   framework code (never imports user_data)
user_data/               your config, datasets, models (gitignored)
tests/                   unit, integration, spike
docs/
  vision/                assumptions & target design
  reference/             as-implemented docs
```

---

## What to Read Next

| Step | Document | Why |
|------|----------|-----|
| 1 | [Data Workflows](../reference/DATA_WORKFLOWS.md) | How data moves (diagrams) |
| 2 | [Module Map](../reference/MODULE_MAP.md) | Packages and status |
| 3 | [Current Status](../planning/CURRENT_STATUS.md) | Sprint progress |
| 4 | [Vision catalog](../vision/README.md) | Binding decisions when designing |
| 5 | [Reference catalog](../reference/README.md) | Deep module docs |

---

## Architecture Rules (short)

- Domain logic does not call external APIs directly — use `infrastructure` adapters.
- Strategies must stay stateless (when implemented).
- Use UTC and `Clock` abstractions — no naive datetimes in domain code.
- Do not import `user_data` from `src/trading_framework/`.

Full rules: `AGENTS.md`, `.cursor/rules/project-architecture.mdc`.
