# Module Map

This map answers **where a responsibility lives**. Read [System Overview](SYSTEM_OVERVIEW.md) for the big picture, then open one capability page below for package entry points. The [dependency rules](DEPENDENCY_RULES.md) state which directions are allowed and which are enforced by tests.

## 1. Repository Boundaries

| Root | Responsibility |
|---|---|
| `src/trading_framework/` | Reusable domain, application, and infrastructure code |
| `apps/` | Separately deployable CLI and dashboard consumers (ADR-0022) |
| `user_data/` | User-owned datasets, definitions, strategies, results, and runtime state |
| `scripts/` | Thin invocations of application use cases |
| `deploy/` | Deployment configuration |
| `tests/` | Framework tests; apps may also have their own tests |

The framework never imports concrete `user_data` modules. The apps consume published application contracts and cannot import research or execution engines or provider adapters directly. See [ADR-0002](../../adr/ADR-0002-separate-src-and-user-data.md) and [ADR-0022](../../adr/ADR-0022-repository-top-level-layout.md).

## 2. Top-Level Package Map

| Package | Owns | Detail |
|---|---|---|
| `core/`, `time/`, `config/` | Shared identifiers, time contracts, configuration boundaries | [Shared foundations](../modules/SHARED_FOUNDATIONS.md) |
| `market/` | Market facts, dataset identity and lifecycle, data-domain contracts | [Market Data](../modules/MARKET_DATA.md) |
| `market_analysis/` | Components, dependency planning, computation and analytical outputs | [Market Analysis](../modules/MARKET_ANALYSIS.md) |
| `model_expression/`, `model_authoring/`, `market_model/`, `signal_model/` | Declarative expressions, authoring, model definitions and evaluation | [Models and DSL](../modules/MODELS_AND_DSL.md) |
| `strategy/` | Stateless strategy composition contracts | [Strategy](../modules/STRATEGY.md) |
| `research/` | Research facts, simulation, analytics and persisted artifacts | [Research](../modules/RESEARCH.md) |
| `execution/` | Runtime execution contracts, state and position management | [Execution](../modules/EXECUTION.md) |
| `application/` | Use-case orchestration across domain contracts | [Applications](../modules/APPLICATIONS.md) |
| `infrastructure/` | Provider, storage and delivery adapters implementing contracts | [Infrastructure](../modules/INFRASTRUCTURE.md) |
| `events/` | Reserved stub; do not treat the future event system as implemented | [Future Event System](../../vision/EVENT_SYSTEM_FUTURE.md) |
| `apps/cli/` | Operator CLI consumer | [Operator CLI](../modules/OPERATOR_CLI.md) |
| `apps/dashboard/` | Read-only research and portfolio consumer | [Dashboard](../modules/DASHBOARD_APPLICATION.md) |

The capability pages group related packages; they are intentionally not a one-file-per-source-directory mirror.

## 3. Workflow-to-Module Map

| Workflow | Orchestration | Main domain packages | Reference |
|---|---|---|---|
| Market Data import and publication | `application/`, `market/` | `market/`, `infrastructure/` | [Market Data](../workflows/MARKET_DATA.md) |
| Signal Research | `application/signal_research/` | `market_analysis/`, `market_model/`, `signal_model/`, `research/` | [Signal Research](../workflows/SIGNAL_RESEARCH.md) |
| Strategy Research | `application/strategy_research/` | `strategy/`, `research/`, `market_analysis/` | [Strategy Research](../workflows/STRATEGY_RESEARCH.md) |
| Strategy Execution | `application/` runtime use cases | `strategy/`, `execution/`, `market/` | [Strategy Execution](../workflows/STRATEGY_EXECUTION.md) |
| Predictive Research | `application/predictive_research/` | `research/predictive/`, Market Analysis inputs | [Research](../modules/RESEARCH.md) |
| Presentation | published projection and app queries | `apps/dashboard/`, `apps/cli/` | [Applications](../modules/APPLICATIONS.md) |

These are independent workflows with shared upstream contracts. See [Research Methodologies](../workflows/RESEARCH_METHODOLOGIES.md) to choose a research path.

## 4. Shared Foundations

[Shared foundations](../modules/SHARED_FOUNDATIONS.md) maps `core/`, `time/` and `config/`. [Time and Alignment](TIME_AND_ALIGNMENT.md) defines the temporal contract.

## 5. Market Data Implementation Map

[Market Data](../modules/MARKET_DATA.md) maps canonical facts, imports, dataset lifecycle, continuous futures and adapters. Its end-to-end paths are in the [Market Data workflow](../workflows/MARKET_DATA.md).

## 6. Market Analysis Implementation Map

[Market Analysis](../modules/MARKET_ANALYSIS.md) maps the component engine. See the [implementation guide](../modules/MARKET_ANALYSIS_MODULE.md), [engine architecture](MARKET_ANALYSIS_ARCHITECTURE.md) and [component catalog](../modules/ANALYSIS_COMPONENT_CATALOG.md).

## 7. Declarative Model Implementation Map

[Models and DSL](../modules/MODELS_AND_DSL.md) maps expression, authoring, Market Model and Signal Model packages. [Model Authoring](../modules/MODEL_AUTHORING.md) gives a runnable example.

## 8. Research Implementation Map

[Research](../modules/RESEARCH.md) maps Signal, Strategy, Robustness and Predictive Research packages, persisted artifacts and application entry points. The [workflow index](../workflows/README.md) explains their boundaries.

## 9. Execution Implementation Map

[Execution](../modules/EXECUTION.md) maps the runtime contracts and implementation. [Strategy Execution](../workflows/STRATEGY_EXECUTION.md) explains the operational flow.

## 10. Visualization and Reporting Map

[Applications](../modules/APPLICATIONS.md) maps presentation boundaries. See [Dashboard](../modules/DASHBOARD_APPLICATION.md) and [Operator CLI](../modules/OPERATOR_CLI.md) for the two deployable consumers.

## 11. User Workspace Map

[User Workspace](USER_WORKSPACE.md) maps the `user_data/` layout and its boundary from `src/`. It is distinct from the execution-scoped [AnalysisWorkspace](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md).

## 12. Dependency Rules

[Dependency Rules](DEPENDENCY_RULES.md) is the canonical direction map. It distinguishes test-enforced boundaries from documented ones and records the known exception.

## 13. Test Map

Use the relevant module page for targeted tests. Cross-cutting import-boundary tests are listed in [Dependency Rules](DEPENDENCY_RULES.md#2-what-is-actually-enforced-by-a-test-today).

## 14. Detailed References

The [reference index](../README.md) routes from the system view to workflows, modules, runbooks and worked examples. ADRs record decision rationale; [vision](../../vision/README.md) records future directions.

## Maintenance

When packages or ownership change, update this map and the affected module page in the same PR. Update the overview only when the system-level story changes.
