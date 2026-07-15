# Developer Guide

Day-one setup for **developers joining the repo**.

- **Role-based overview** (recruiter, data engineer, software engineer, …): **[README § Start here](../../README.md#start-here--pick-your-path)**
- **Documentation index:** [docs/README.md](../README.md)
- **AI agents:** `AGENTS.md` at the repository root

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

scripts/                 thin CLIs (databento, market_data, signal_research, strategy_research, robustness_research, demo)
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

Depends on your focus — the README [Start here](../../README.md#start-here--pick-your-path) table links to the right depth.

| Focus | Read next |
|-------|-----------|
| **Data / pipelines** | [DATA_WORKFLOWS.md](../reference/DATA_WORKFLOWS.md) → [DATA_MODULE_UPDATED.md](../reference/modules/DATA_MODULE_UPDATED.md) |
| **Code / architecture** | [MODULE_MAP.md](../reference/MODULE_MAP.md) → [adr/](../adr/README.md) |
| **Research workflows** | [RESEARCH_METHODOLOGIES.md](../reference/RESEARCH_METHODOLOGIES.md) → [DATA_WORKFLOWS.md](../reference/DATA_WORKFLOWS.md) |
| **Sprint context** | [CURRENT_STATUS.md](../planning/CURRENT_STATUS.md) → [ROADMAP.md](../planning/ROADMAP.md) |
| **Design decisions** | [Vision catalog](../vision/README.md) → [Reference catalog](../reference/README.md) |

---

## Architecture rules (short)

- Domain logic does not call external APIs directly — use `infrastructure` adapters.
- Strategies must stay stateless (when implemented).
- Use UTC and `Clock` abstractions — no naive datetimes in domain code.
- Do not import `user_data` from `src/trading_framework/`.
- Signal Research, Strategy Research and Execution are workflow-independent.

Full rules: `AGENTS.md`, `.cursor/rules/project-architecture.mdc`.
