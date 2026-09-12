# System Overview

This is the shortest route from the product idea to the implemented system. It describes current responsibilities; [Vision](../../vision/README.md) records future directions, [Roadmap](../../planning/ROADMAP.md) records planned delivery, and [ADRs](../../adr/README.md) record why durable choices were made.

## 1. High-Level Architecture

The framework is a modular monolith with separately deployable consumers. Market facts enter through provider/file adapters, become published datasets, and feed reusable Market Analysis and declarative models. Research and Execution independently consume those contracts; presentation reads persisted or safely projected results.

```text
External sources → Infrastructure adapters → Market datasets
                                           ↓
                              Market Analysis components
                                           ↓
                            Market Model + Signal Model
                                           ↓
                                  Strategy definition
                                  ├─→ Research → persisted evidence
                                  └─→ Execution → runtime state
                                                  ↓
                                 CLI / Dashboard consumers
```

The [Module Map](MODULE_MAP.md) names packages. [Dependency Rules](DEPENDENCY_RULES.md) names allowed and forbidden directions.

## 2. Framework Core and User Workspace

`src/trading_framework/` holds reusable contracts, domain logic, application use cases and adapters. `apps/cli/` and `apps/dashboard/` are deployable consumers. `user_data/` holds user-owned data, definitions, strategies and run artifacts; no framework module imports concrete user data. See [User Workspace](USER_WORKSPACE.md), [ADR-0002](../../adr/ADR-0002-separate-src-and-user-data.md) and [ADR-0022](../../adr/ADR-0022-repository-top-level-layout.md).

## 3. Market Data

Market Data owns canonical facts, dataset identity, validation, publication and historical retrieval. Provider-specific representations stop at infrastructure adapters. Published `DatasetRef` versions are reproducible research inputs. Existing paths include file/archive and exchange historical imports, local Parquet storage, trade-to-bar derivation and continuous futures materialization; the [Market Data workflow](../workflows/MARKET_DATA.md) describes each path and its limits.

Package placement: [Market Data module](../modules/MARKET_DATA.md). Future synchronization, missing-range and live-recording targets: [Market Data Future](../../vision/MARKET_DATA_FUTURE.md).

## 4. Market Analysis

Market Analysis turns market facts into reusable Features, Structures and States. A component request resolves dependencies, plans a DAG, computes outputs and applies timeframe/availability rules. Component identity and cache scope make reuse explicit. See [Market Analysis module](../modules/MARKET_ANALYSIS.md), [engine architecture](MARKET_ANALYSIS_ARCHITECTURE.md), [component catalog](../modules/ANALYSIS_COMPONENT_CATALOG.md), and [time alignment](TIME_AND_ALIGNMENT.md).

## 5. Declarative Models and DSL

Model authoring produces explicit Market Model and Signal Model definitions over controlled expressions and analytical component requests. Definitions are reusable across research and runtime consumers without arbitrary data-frame access. See [Models and DSL](../modules/MODELS_AND_DSL.md) and the [authoring example](../modules/MODEL_AUTHORING.md).

## 6. Research and Simulation

Signal, Strategy, Robustness and Predictive Research answer different questions and persist their own evidence. Strategy simulation uses the Strategy contract, but does not become Execution state. Analytics and reporting read persisted results. See [Research module](../modules/RESEARCH.md), [methodology chooser](../workflows/RESEARCH_METHODOLOGIES.md), [Signal Research](../workflows/SIGNAL_RESEARCH.md) and [Strategy Research](../workflows/STRATEGY_RESEARCH.md).

## 7. Results and Visualization

Research results are stored as versioned artifacts. The dashboard reads a safe public projection and selected read models; public pages do not load private workspace paths. Visualization does not execute research or control runtime execution. See [Dashboard](../modules/DASHBOARD_APPLICATION.md), [Applications](../modules/APPLICATIONS.md), and [ADR-0034](../../adr/ADR-0034-portfolio-publication-boundary.md).

## 8. Live Execution

The built execution slice is a provider-neutral dry-run with simulated orders, runtime state, persistence and status reporting. Strategy decisions, operational risk and broker/delivery concerns have separate owners. Do not infer support for real trading from the dry-run path. See [Execution module](../modules/EXECUTION.md), [Strategy Execution workflow](../workflows/STRATEGY_EXECUTION.md), and [future runtime direction](../../vision/EXECUTION_RUNTIME_FUTURE.md).

## 9. Operator CLI

`apps/cli/` exposes application workflows through the `trading-cli` command surface. It is a consumer, not a second research engine. See [Operator CLI](../modules/OPERATOR_CLI.md) for commands, configuration boundaries and exit codes.

## 10. Shared Domain Contracts

[Domain Model](DOMAIN_MODEL.md) defines ownership; [Architecture Principles](ARCHITECTURE_PRINCIPLES.md) defines cross-cutting invariants; [Time and Alignment](TIME_AND_ALIGNMENT.md) defines clock and availability semantics; [Data Representation Policy](DATA_REPRESENTATION_POLICY.md) distinguishes accepted target carriers from the current implementation. [Analysis Workspace and Derived Data](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) provides the detailed execution-scoped analytical contract.

## 11. Technology Overview

The core uses Python and Parquet-backed local datasets. Polars serves current
resampling/alignment and selected columnar reads; Market Analysis components
still use `AnalysisDataView` and NumPy adapters rather than an implemented
`MarketFrame` bulk engine. The Streamlit dashboard serves sanitized public
projection releases and has a separate read-only query compatibility layer.
Technology belongs behind explicit adapters or consumer boundaries; dependency
direction is more important than any particular library.

## 12. Development Directions

Current-state descriptions above are deliberately separate from targets. Follow [Vision](../../vision/README.md) for future Market Data, Time Model, Market Analysis, research-space, event-system and execution-runtime directions. Follow [Roadmap](../../planning/ROADMAP.md) for phase status and sequencing.

## 13. Detailed References

Start with the [Module Map](MODULE_MAP.md), choose one [module guide](../modules/README.md), then open the relevant [workflow](../workflows/README.md) or [runbook](../runbooks/README.md). The [reference index](../README.md) lists every reference area.
