# Workflow Reference

A workflow explains how modules cooperate end to end. It does not redefine module ownership. Start with the [System Overview](../system/SYSTEM_OVERVIEW.md) and [Module Map](../system/MODULE_MAP.md) if the boundaries are unfamiliar.

| Workflow | What it covers |
|---|---|
| [Market Data](MARKET_DATA.md) | Import, validation, publication, historical access and derived datasets |
| [Signal Research](SIGNAL_RESEARCH.md) | Analytical scopes, model evaluation, occurrences and persisted outcomes |
| [Strategy Research](STRATEGY_RESEARCH.md) | Strategy simulation, trades/equity artifacts and analytics |
| [Strategy Execution](STRATEGY_EXECUTION.md) | Runtime decisions, state, risk separation and persistence |
| [Research Methodologies](RESEARCH_METHODOLOGIES.md) | Which research question to ask and how to evaluate it |

The methodology chooser links to focused [Signal](methodologies/SIGNAL_RESEARCH.md), [Model](methodologies/MODEL_RESEARCH.md), [Strategy](methodologies/STRATEGY_RESEARCH.md), [Robustness](methodologies/ROBUSTNESS_RESEARCH.md), [Predictive](methodologies/PREDICTIVE_RESEARCH.md) and [Portfolio](methodologies/PORTFOLIO_RESEARCH.md) method pages.

Signal Research, Strategy Research and Strategy Execution are independent workflows with shared upstream contracts, not stages of one mandatory pipeline.
