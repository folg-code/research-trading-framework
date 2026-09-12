# Applications and presentation — implementation map

This page records the existing packages and entry points for applications and presentation. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Application use cases

`src/trading_framework/application/` orchestrates domain contracts without
owning market facts, analytical rules, strategy definitions or adapter
implementations. Its packages follow use cases rather than one generic
pipeline:

| Use case | Package |
|---|---|
| Market-data import and publication | `application/market_data/` |
| Analytical requests | `application/market_analysis/` |
| Reusable model evaluation | `application/model_evaluation/` |
| Signal Research | `application/signal_research/` |
| Strategy Research | `application/strategy_research/` |
| Robustness Research | `application/robustness_research/` |
| Predictive Research | `application/predictive_research/` |
| Execution runtime use cases | `application/execution/` |

Each workflow reference in the [workflow index](../workflows/README.md)
describes the orchestration path and persisted output. Infrastructure adapters
implement external ports consumed through these use cases.

## Presentation and reporting

### Responsibilities

| Responsibility | Package |
|---|---|
| Read-only analytics | `research/analytics/` |
| Signal research reports | `research/reporting/signal_research/` |
| Strategy dashboards | strategy analytics and reporting packages |
| Robustness reports | `research/robustness/` reporting packages |
| Live dashboard state | execution read-model adapters |
| Demo generation | `scripts/demo/` |
| Live dashboard delivery | `scripts/portfolio_live/` (aiohttp); `apps/dashboard` Live Paper page (status GET) |
| Predictive Research dashboard delivery | `apps/dashboard/src/dashboard_app/publication/` plus `views/study.py`; one projection-backed representative view in `pages/10_Predictive_Research.py` (Sprint 061) |

### Boundary

Visualization reads:

- persisted research artifacts,
- persisted analytics,
- runtime state.

Visualization does not execute research or control execution.

---
