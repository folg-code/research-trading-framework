# Developer Guide

Day-one setup for **developers joining the repo**.

- **System reading path** (developer or agent): **[Documentation § Learn the system](../README.md#learn-the-system)**
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

Optional Predictive Research extras (`ml` = scikit-learn; `ml-trees` =
XGBoost / LightGBM / CatBoost; `dl` = CPU PyTorch). Default
`uv sync --locked --dev` stays extra-free. Standard unit tests use
`-m "not ml and not ml_trees and not torch"`. Optional extras:

```bash
uv sync --locked --extra ml --dev
uv run pytest -m ml

uv sync --locked --extra ml --extra ml-trees --dev
uv run pytest -m ml_trees

uv sync --locked --extra dl --dev
TRADING_FRAMEWORK_RUN_TORCH_TESTS=1 uv run pytest -m torch
```

---

## Delivery paths

Every change follows intake, context and risk classification, planning or
approval, implementation, verification, review, documentation impact check,
and delivery. Choose the path from the outcome and urgency; classify risk
separately. Neither a small diff nor a high-risk label alone requires a PRD,
roadmap, phase, or sprint.

| Path | Use when | Starting context |
|---|---|---|
| Sprint capability | A product outcome needs coordinated tasks or capability sequencing. | Approved PRD or roadmap outcome and sprint plan. |
| Standalone fix or small change | One bounded correction or change has a clear outcome. | A clear request or ticket, scope, and acceptance criteria. |
| Standalone high-risk task | One bounded outcome has material risk but needs no new product decision or coordinated sprint. | An approved ticket with objective, acceptance criteria, scope, dependencies, risk, relevant context, verification plan, and rollback plan when data or production may be affected. |
| Hotfix | An ongoing incident or critical regression needs prompt restoration. A deadline or high risk alone does not qualify. | Incident or regression evidence, restoration objective, affected scope, and verification/rollback approach. |
| Maintenance | Documentation, tests, refactoring, or debt repayment has a clear bounded outcome. | A clear request or ticket and scope; acceptance criteria where behavior or contracts may change. |

Risk determines the checks and approvals on every path:

| Risk | Planning | Verification | Review |
|---|---|---|---|
| Low: local, reversible, covered by existing validation, with no public-behavior, architecture, dependency, data, security, permission, or infrastructure impact | Implicit when obvious | Targeted checks | Self-review |
| Standard: everything else, including uncertain classification | Short explicit plan | Targeted and affected integration checks | Independent review in a fresh context |
| High: material data, security, privacy, permission, cross-cutting architecture, public-contract, production, rollback, or requirements risk | Explicit plan and human approval before implementation | Expanded risk-based checks | Independent review in a fresh context |

Use the high-risk task requirements for any standalone change classified high,
including a hotfix or maintenance task. Triage architecture impact before
approving a PRD or high-risk standalone plan and whenever work crosses module
or contract boundaries. Cross-cutting decisions require human approval.
If requirements are unresolved or the work grows into coordinated outcomes,
recommend discovery, a PRD, roadmap, or sprint plan and obtain the human's
decision before that transition.

A hotfix restores service with the smallest safe scope. It keeps PR, CI, and
review; bypassing any one gate requires separate explicit maintainer approval
for that incident. Record cause, verification, and follow-up work in the issue
or PR instead of silently expanding the emergency change. Outside a sprint,
the PR may be the only completion record, but required planning and approvals
still apply, and affected behavior documentation must be updated. See
[Git Delivery Workflow](../../AGENTS.md#git-delivery-workflow)
for target branches and merge rules.

---

## Credentials

The default install and the standard test suite need no credentials.

| Variable | Purpose | Required |
|---|---|---|
| `TRADING_FRAMEWORK_BINANCE_API_KEY` | Sent as the `X-MBX-APIKEY` header on public Binance USD-M market-data GETs only (`/fapi/v1/klines`, used by the historical OHLCV import). Raises the weight-based rate limit; nothing else. | No — unset means anonymous requests at the default rate limit; import still works. |

Set it as a real environment variable in your own shell/session. Never place
it in a committed file, never in a file under `user_data/`, and it never
appears in a log line, an error message, or `import_manifest.json` (which
records only the boolean `api_key_used`). This is the one place this key is
documented; see `docs/adr/ADR-0025-binance-usdm-historical-klines-import.md`
for the design rationale.

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
src/trading_framework/   framework code (never imports user_data or apps)
├── application/         use cases — orchestration entry points
├── market/              bars, trades, datasets, contracts, continuous
├── market_analysis/     components, planning, execution, frames
├── model_expression/    declarative IR and evaluation
├── market_model/ · signal_model/ · strategy/
├── research/            envelopes, simulation, analytics
├── infrastructure/      Parquet, Databento, CSV, registry
└── core/ · time/ · config/

apps/dashboard/          read-only Streamlit + DuckDB research dashboard
scripts/                 thin CLIs (see scripts/README.md)
deploy/                  AWS containers + local AWS runbook home
artifacts/demo/          generated portfolio HTML (from scripts/demo)
tests/                   unit, integration, fixtures, spike
docs/                    vision, reference, planning, adr, agents, onboarding
scratch/                 local-only logs / one-off probes (gitignored)
user_data/               your storage, config, models (gitignored)
```

### Navigation tiers

| Tier | Paths | In default Explorer? |
|------|-------|----------------------|
| First-class | `src/`, `apps/`, `scripts/`, `docs/`, `tests/` | Yes |
| Support | `deploy/`, `artifacts/` | Yes |
| Local-only | `scratch/`, `user_data/`, `.venv/`, tool caches | `scratch`/caches hidden; `user_data` visible in Explorer, excluded from search |

Binding layout: **ADR-0022**. Pass `storage_root: Path` from `user_data/` into
application functions. Framework code must not import `user_data/` modules.
`apps/*` must not import research/execution engines or provider/importer adapters.

Dashboard locally:

```powershell
cd apps/dashboard
uv sync
$env:DASHBOARD_STORAGE_ROOT = (Resolve-Path ..\..\user_data).Path
uv run streamlit run Project_Overview.py
```

---

## Portfolio demo

Fastest way to see all workflows and dashboards offline:

```bash
uv run python scripts/demo/run_portfolio_demo.py --full --open
```

See [scripts/demo/README.md](../../scripts/demo/README.md).

---

## What to read next

Depends on your focus — the [documentation reading path](../README.md#learn-the-system) links to the right depth.

| Focus | Read next |
|-------|-----------|
| **Data / pipelines** | [MARKET_DATA.md](../reference/workflows/MARKET_DATA.md) |
| **Code / architecture** | [MODULE_MAP.md](../reference/system/MODULE_MAP.md) → [adr/](../adr/README.md) |
| **Research workflows** | [RESEARCH_METHODOLOGIES.md](../reference/workflows/RESEARCH_METHODOLOGIES.md) → [MARKET_DATA.md](../reference/workflows/MARKET_DATA.md) |
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
