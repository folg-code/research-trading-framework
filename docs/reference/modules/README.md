# Module Guides

Read [System Overview](../system/SYSTEM_OVERVIEW.md) first, then [Module Map](../system/MODULE_MAP.md) to locate a responsibility. These guides group related packages by capability; they are not a file-for-file mirror of `src/`. Workflows describe end-to-end behavior separately.

## Capability and package ownership

| Guide | Packages and responsibility |
|---|---|
| [Shared Foundations](SHARED_FOUNDATIONS.md) | `core/`, `time/`, `config/` — common types and boundaries |
| [Market Data](MARKET_DATA.md) | `market/` and import/storage paths — canonical facts and datasets |
| [Market Analysis](MARKET_ANALYSIS.md) | `market_analysis/` — analytical components and engine |
| [Models and DSL](MODELS_AND_DSL.md) | `model_expression/`, `model_authoring/`, `market_model/`, `signal_model/` |
| [Strategy](STRATEGY.md) | `strategy/` — stateless composition contract |
| [Research](RESEARCH.md) | `research/` and research use cases — simulation, analytics, artifacts |
| [Execution](EXECUTION.md) | `execution/` — runtime contracts and state |
| [Applications](APPLICATIONS.md) | `application/` and presentation boundaries |
| [Infrastructure](INFRASTRUCTURE.md) | `infrastructure/` — external adapters |
| [Operator CLI](OPERATOR_CLI.md) | `apps/cli/` consumer and commands |
| [Dashboard](DASHBOARD_APPLICATION.md) | `apps/dashboard/` consumer and public projection |

## Detailed contracts and authoring

- [Market Analysis implementation guide](MARKET_ANALYSIS_MODULE.md) and [component catalog](ANALYSIS_COMPONENT_CATALOG.md).
- [Model Authoring](MODEL_AUTHORING.md), [Strategy Authoring](STRATEGY_AUTHORING.md) and [Strategy Examples](STRATEGY_EXAMPLES.md).
- [Predictive Promotion](PREDICTIVE_PROMOTION.md) and [Predictive Verdict](../PREDICTIVE_VERDICT.md).

For execution-scoped analytical storage, see [Analysis Workspace and Derived Data](../system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md). For user-owned files and results, see [User Workspace](../system/USER_WORKSPACE.md).
