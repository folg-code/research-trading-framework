# Developer Guide

Day-one setup. Documentation index: **[../README.md](../README.md)**.  
Project overview (workflows, stack, architecture): **[../../README.md](../../README.md)**.

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

Optional for inspection HTML spikes and portfolio demo:

```bash
uv pip install plotly
```

---

## Tech stack (short)

| Concern | Choice |
|---------|--------|
| Runtime | Python 3.12+, type hints, Pydantic v2 |
| Tables / analytics | Polars |
| Numerics | NumPy (analysis adapters), Numba (simulation kernel) |
| Persistence | PyArrow Parquet, JSON metadata registry |
| Import adapters | CSV, Databento DBN (infrastructure only) |
| Dashboards | Lightweight Charts (strategy), Plotly (inspection spikes) |
| Quality | Ruff, mypy, pytest, pre-commit |

---

## Repository layout

```text
src/trading_framework/   framework code (never imports user_data)
├── application/         use cases — orchestration entry points
├── market/              bars, trades, datasets, contracts, continuous
├── market_analysis/     components, planning, execution, frames
├── model_expression/    declarative IR and evaluation
├── market_model/ · signal_model/ · strategy/
├── research/            envelopes, simulation, analytics
├── infrastructure/      Parquet, Databento, CSV, registry
└── core/ · time/ · config/

scripts/                 thin CLIs (databento, market_data, strategy_research, demo)
tests/                   unit, integration, fixtures, spike (manual HTML)
user_data/               your storage, config, models (gitignored)
docs/                    vision, reference, planning, adr
demo/output/             generated portfolio HTML (from demo script)
```

**Boundary:** pass `storage_root: Path` from `user_data/` into application functions. Framework code must not import `user_data/` modules.

---

## Portfolio demo

Fastest way to see all workflows and dashboards offline:

```bash
uv run python scripts/demo/run_portfolio_demo.py --full --open
```

See [scripts/demo/README.md](../../scripts/demo/README.md).

---

## What to read next

| Step | Document | Why |
|------|----------|-----|
| 1 | [Data Workflows](../reference/DATA_WORKFLOWS.md) | How data moves (diagrams) |
| 2 | [Module Map](../reference/MODULE_MAP.md) | Packages and status |
| 3 | [Current Status](../planning/CURRENT_STATUS.md) | Sprint progress |
| 4 | [Vision catalog](../vision/README.md) | Binding decisions when designing |
| 5 | [Reference catalog](../reference/README.md) | Deep module docs |

---

## Architecture rules (short)

- Domain logic does not call external APIs directly — use `infrastructure` adapters.
- Strategies must stay stateless (when implemented).
- Use UTC and `Clock` abstractions — no naive datetimes in domain code.
- Do not import `user_data` from `src/trading_framework/`.
- Signal Research, Strategy Research and Execution are workflow-independent.

Full rules: `AGENTS.md`, `.cursor/rules/project-architecture.mdc`.
