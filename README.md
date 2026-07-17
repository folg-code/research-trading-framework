# Trading Research Framework

Trading Research Framework is a modular Python platform for systematic trading research and
paper/live-dry-run execution.

The domain is trading, but the main value is the architecture: reproducible data pipelines,
declarative research definitions, stable domain contracts, immutable artifacts, and a clear boundary
between framework code and user-owned research work.

```text
Trading is the domain.
Architecture is the project value.
```

---

## Why This Exists

Most trading research systems start as scripts. Data loading, feature engineering, signal logic,
backtesting, charts and broker calls gradually merge into one fragile workflow. That makes results
hard to reproduce, hard to review, and dangerous to move toward execution.

This framework was built around a different premise:

1. Market data should be normalized, versioned and published before it is used.
2. Research should produce immutable artifacts, not overwriteable notebook state.
3. Strategy execution should not depend on research dashboards or historical datasets.
4. Users should extend the system through contracts and declarative definitions, not by modifying
   the framework core.
5. Visualization should explain what happened, not become the source of truth.

The result is a research and execution platform where the same engineering ideas could apply to
other Data Engineering and Research Engineering domains: ingestion, normalization, reproducible
experiments, stateful runtime services, and read-only public dashboards.

---

## Start Here

| If you want to understand... | Start with | Then go deeper |
|------------------------------|------------|----------------|
| The project vision | [Why This Exists](#why-this-exists) | [Architecture Philosophy](#architecture-philosophy) |
| What the framework can show | [Engineering Showcase](#engineering-showcase) | [Portfolio demo docs](scripts/demo/README.md) |
| Data pipelines and lifecycle | [Data As Product](#data-as-product) | [DATA_WORKFLOWS.md](docs/reference/DATA_WORKFLOWS.md) |
| Module ownership and APIs | [Core Boundaries](#core-boundaries) | [MODULE_MAP.md](docs/reference/MODULE_MAP.md) |
| Research methodology | [Independent Research Workflows](#independent-research-workflows) | [RESEARCH_METHODOLOGIES.md](docs/reference/RESEARCH_METHODOLOGIES.md) |
| Current status and roadmap | [Where The Project Is Now](#where-the-project-is-now) | [CURRENT_STATUS.md](docs/planning/CURRENT_STATUS.md), [ROADMAP.md](docs/planning/ROADMAP.md) |

---

## Architecture Philosophy

### Core Boundaries

The strongest architectural decision is the split between reusable framework code and user-owned
research workspace.

```text
src/        framework core
user_data/  local datasets, configs, strategies, research outputs and runtime state
```

`src/` owns stable contracts, orchestration, storage interfaces, domain models, provider adapters,
execution runtime, broker abstractions and public application workflows.

`user_data/` owns private or local material: datasets, configuration, user components, study
definitions, strategy definitions, generated runs and portfolio artifacts.

The rule is simple:

```text
Framework Core never imports user_data.
```

That boundary keeps the framework reusable while still allowing real research work to happen outside
the package.

Deep reference: [MODULE_MAP.md](docs/reference/MODULE_MAP.md).

### Declarative Extension

The framework is designed to be extended through definitions:

- Market Analysis components,
- Market Models,
- Signal Models,
- Strategy Models,
- research study specs,
- execution runtime configuration.

The user should not need to understand the internal DAG planner, storage layout, alignment engine or
execution adapters just to express a new idea. Definitions are executed through stable public
contracts; the framework handles orchestration, alignment, persistence and reporting.

Deep reference: [RESEARCH_METHODOLOGIES.md](docs/reference/RESEARCH_METHODOLOGIES.md).

### Research Is Not Execution

Research and execution are intentionally separate capabilities.

```text
Signal Research      Strategy Research      Strategy Execution
       |                    |                       |
       +------ shared domain contracts -------------+
```

Signal Research can evaluate whether a market condition predicts forward behavior. Strategy Research
can simulate complete entries, exits and risk rules. Strategy Execution can run selected strategy
logic against live market data without loading research reports or historical experiment state.

This separation prevents a common failure mode: treating a backtest dashboard as an executable
trading system.

Deep reference: [DATA_WORKFLOWS.md](docs/reference/DATA_WORKFLOWS.md).

### Immutable Data And Artifacts

Published datasets are treated as immutable inputs. Research runs, equity curves, trades, analysis
reports and dashboards are immutable outputs. A result should be explainable after the fact: which
dataset version, which model definition, which runtime assumptions and which code path produced it.

This is why the framework favors manifests, lineage, registries and standalone HTML reports over
ad-hoc notebook state.

---

## Data As Product

Market data is not just loaded into memory. It moves through an explicit lifecycle:

```text
external source
  -> normalize
  -> validate
  -> partitioned storage
  -> finalize
  -> publish
  -> query by DatasetRef
```

For futures research, multiple contract datasets can be materialized into continuous instruments
using explicit roll schedules. Derived OHLCV bars are built once and reused by downstream research.

The important design choice is that consumers do not depend on vendor files or local paths. They
consume published, provider-independent market facts.

Deep reference: [DATA_WORKFLOWS.md](docs/reference/DATA_WORKFLOWS.md).

---

## Independent Research Workflows

The framework supports several research workflows. They are related, but not one mandatory pipeline.

### Historical Research

Normalizes external data, builds continuous futures, derives OHLCV and publishes reusable datasets.
This creates the factual base for analysis and simulation.

### Model Research

Evaluates declarative Market Models and Signal Models over analysis frames, then measures forward
outcomes such as MFE, MAE and hit rate. Its purpose is to understand behavior before turning ideas
into complete strategies.

### Strategy Research

Combines market conditions, signal gates, exits and risk rules into bar-sequential simulations. It
produces trades, equity curves, KPIs and dashboard artifacts.

### Robustness Research

Tests whether a strategy result survives parameter sweeps, walk-forward slices, stress assumptions
and Monte Carlo variation. Its purpose is not to prove certainty; it is to expose fragility.

### Live Dry-Run Execution

Runs selected execution logic against live BTCUSDT market data with simulated orders only. It proves
the execution architecture without connecting real capital.

Deep reference: [RESEARCH_METHODOLOGIES.md](docs/reference/RESEARCH_METHODOLOGIES.md).

---

## Live Execution As Architecture Proof

The live dashboard is intentionally not presented as the product. It is a visualization of a running
pipeline:

```text
Binance market data
  -> AWS worker
  -> execution runtime
  -> paper broker
  -> persisted execution state
  -> REST status API
  -> VPS live dashboard
```

The dashboard shows candles, simulated fills, position state, equity and heartbeat freshness. The
engineering value is behind it: provider abstraction, runtime state persistence, read-only API
surface, isolated dashboard history and no browser exposure of AWS internals.

Runbook: [AWS_BTC_FUTURES_DRY_RUN.md](docs/reference/AWS_BTC_FUTURES_DRY_RUN.md).
VPS dashboard: [scripts/portfolio_live/README.md](scripts/portfolio_live/README.md).

---

## Engineering Showcase

The portfolio is not a screenshot gallery. Each demo is evidence of a workflow and a design decision.

| Demo | What it proves | Entry point |
|------|----------------|-------------|
| Historical Research | Vendor data becomes provider-independent, reusable datasets | [DATA_WORKFLOWS.md](docs/reference/DATA_WORKFLOWS.md) |
| Model Research | Declarative models can be studied before execution | [RESEARCH_METHODOLOGIES.md](docs/reference/RESEARCH_METHODOLOGIES.md) |
| Strategy Research | Complete strategy assumptions produce trades, KPIs and equity | `demo/output/00_strategy_dashboard_nq_half_year.html` |
| Robustness Research | Strategy claims can be stress-tested across assumptions | `demo/output/07_robustness_dashboard.html` |
| Live Execution | Runtime state can be exposed safely through a read-only dashboard | `https://dryrun.filipf.online` |
| Portfolio Hub | The framework story, methodology and reports in one browser entry point | `demo/output/index.html` |

Generate the local portfolio bundle:

```bash
uv pip install plotly
uv run python scripts/demo/run_portfolio_demo.py --full --open
```

Portfolio docs: [scripts/demo/README.md](scripts/demo/README.md).

---

## Scale Reference

The NQ half-year demo exists to show that the architecture is not only conceptual.

Reference run:

- 45M+ Databento tick trades normalized,
- 44M+ continuous futures trades materialized,
- 177k+ one-minute OHLCV bars derived,
- 1,400+ simulated strategy trades,
- strategy research run in roughly seconds once preprocessing is complete.

The important point is not the exact benchmark. It is the separation of concerns: expensive
preprocessing is materialized once; research consumes published datasets through stable contracts.

Details: [DATA_WORKFLOWS.md section 1.1](docs/reference/DATA_WORKFLOWS.md#11-reference-scale-nq-half-year-demo).

---

## Where The Project Is Now

The framework currently includes:

- market data import and publication,
- continuous futures materialization,
- reusable market analysis components,
- declarative Market and Signal Models,
- Signal Research and Model Research workflows,
- Strategy Research simulation and dashboards,
- Robustness Research reports,
- AWS BTC futures dry-run execution,
- VPS live dashboard server,
- portfolio demo hub.

Current status: [CURRENT_STATUS.md](docs/planning/CURRENT_STATUS.md).
Roadmap: [ROADMAP.md](docs/planning/ROADMAP.md).

---

## Quick Start For Developers

```bash
git clone <repo-url>
cd research-trading-framework
uv sync --locked --dev
uv run pytest
```

Quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Developer onboarding: [DEVELOPER_GUIDE.md](docs/onboarding/DEVELOPER_GUIDE.md).
AI contributors: [AGENTS.md](AGENTS.md).

---

## Documentation Map

| Document | Responsibility |
|----------|----------------|
| [docs/README.md](docs/README.md) | Documentation index and reading paths |
| [MODULE_MAP.md](docs/reference/MODULE_MAP.md) | Module structure, ownership, dependencies and entry points |
| [DATA_WORKFLOWS.md](docs/reference/DATA_WORKFLOWS.md) | Data lifecycle, ingest, storage, analysis and execution flows |
| [RESEARCH_METHODOLOGIES.md](docs/reference/RESEARCH_METHODOLOGIES.md) | Research workflow methodology and usage |
| [AWS_BTC_FUTURES_DRY_RUN.md](docs/reference/AWS_BTC_FUTURES_DRY_RUN.md) | AWS dry-run execution runbook |
| [scripts/demo/README.md](scripts/demo/README.md) | Portfolio demo generation and artifact guide |
| [scripts/portfolio_live/README.md](scripts/portfolio_live/README.md) | VPS live dashboard server |
| [docs/adr/](docs/adr/) | Architecture decision records |

---

## License

Private research project.
