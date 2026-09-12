# As-Implemented Reference

This layer describes current behavior. Start at the [System Overview](system/SYSTEM_OVERVIEW.md), then use the [Module Map](system/MODULE_MAP.md) to locate ownership. For future intentions see [Vision](../vision/README.md); for decision history see [ADRs](../adr/README.md).

| Area | Start here | When to read |
|---|---|---|
| System | [System index](system/README.md) | Architecture, domain ownership, dependencies, time and data contracts |
| Modules | [Module guides](modules/README.md) | Package responsibilities and implementation entry points |
| Workflows | [Workflow index](workflows/README.md) | End-to-end Market Data, Research and Execution paths |
| Runbooks | [Runbook index](runbooks/README.md) | Operating the local/AWS dry-run and checking its pipeline |
| Examples | [Predictive BTC study](examples/BTC_PREDICTIVE_STUDY.md), [Signal Quality BTC study](examples/BTC_SIGNAL_QUALITY_STUDY.md) | Worked evidence, not universal behavior |

The [Predictive Verdict](PREDICTIVE_VERDICT.md) explains the versioned analyst verdict artifact. Detailed authoring examples and the component catalog live under [Modules](modules/README.md).

## Completed-phase coverage

This is the current-reference route for delivered phase outcomes. The
[archive](../archive/README.md) keeps sprint evidence; an accepted ADR may
authorize work without proving that its implementation shipped.

| Delivered track | Current contract |
|---|---|
| Repository foundation and boundaries | [System overview](system/SYSTEM_OVERVIEW.md), [dependency rules](system/DEPENDENCY_RULES.md) |
| Market Data: OHLCV, DBN trades, derived bars, continuous futures, Binance historical import | [Market Data workflow](workflows/MARKET_DATA.md) |
| Market Analysis and multitimeframe model composition | [Market Analysis module](modules/MARKET_ANALYSIS.md), [implementation guide](modules/MARKET_ANALYSIS_MODULE.md), [time and alignment](system/TIME_AND_ALIGNMENT.md) |
| Signal and Model Research | [Signal Research](workflows/SIGNAL_RESEARCH.md), [model methodology](workflows/methodologies/MODEL_RESEARCH.md) |
| OHLCV Strategy and Robustness Research | [Strategy Research](workflows/STRATEGY_RESEARCH.md), [Robustness methodology](workflows/methodologies/ROBUSTNESS_RESEARCH.md) |
| BTC futures dry-run execution and status | [Strategy Execution](workflows/STRATEGY_EXECUTION.md), [Execution module](modules/EXECUTION.md), [runbooks](runbooks/README.md) |
| Predictive Research and model-family comparison | [Predictive methodology](workflows/methodologies/PREDICTIVE_RESEARCH.md), [Research module](modules/RESEARCH.md) |
| Operator CLI, custom strategy authoring, bracket exit and sizing | [Operator CLI](modules/OPERATOR_CLI.md), [Strategy Authoring](modules/STRATEGY_AUTHORING.md), [Strategy Examples](modules/STRATEGY_EXAMPLES.md) |
| Predictive artifact promotion and catalog components | [Predictive Promotion](modules/PREDICTIVE_PROMOTION.md), [component catalog](modules/ANALYSIS_COMPONENT_CATALOG.md) |
| Analyst verdict, SampleSpec and Signal Quality | [Predictive Verdict](PREDICTIVE_VERDICT.md), [Predictive methodology](workflows/methodologies/PREDICTIVE_RESEARCH.md), [worked study](examples/BTC_SIGNAL_QUALITY_STUDY.md) |
| Delivered public portfolio slices through Sprint 061 | [Dashboard Application](modules/DASHBOARD_APPLICATION.md), [Applications](modules/APPLICATIONS.md) |

Phase 16D remains active; the table covers its delivered slices rather than
the full future Research Application. The accepted `MarketFrame` decision in
ADR-MA-014 is likewise not proof that a bulk `MarketFrame` implementation is
present; the [Market Analysis implementation guide](modules/MARKET_ANALYSIS_MODULE.md)
states the current boundary.

## Reading rule

Use the smallest page that answers the question. A workflow explains how modules cooperate; a module guide explains what a package owns; an ADR explains why a durable decision was made. Check implementation claims against the relevant code and tests when changing behavior.
