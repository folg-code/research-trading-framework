# Workflow Reference

A workflow is executable orchestration showing how modules cooperate end to
end. It does not redefine module ownership, methodology or every ordered data
transformation as a pipeline. Start with [Terminology](../system/TERMINOLOGY.md),
the [System Overview](../system/SYSTEM_OVERVIEW.md) and [Module
Map](../system/MODULE_MAP.md) if the boundaries are unfamiliar.

| Workflow | What it covers |
|---|---|
| [Market Data](MARKET_DATA.md) | Import, validation, publication, historical access and derived datasets |
| [Signal Research](SIGNAL_RESEARCH.md) | Technical workflow behind the Market & Signal Study product flow; explicit Market Model-only, Signal Model-only and combined scopes |
| [Strategy Research](STRATEGY_RESEARCH.md) | Strategy simulation, trades/equity artifacts and analytics |
| [Strategy Execution](STRATEGY_EXECUTION.md) | Runtime decisions, state, risk separation and persistence |
| [Research Methodologies](RESEARCH_METHODOLOGIES.md) | Which research question to ask and how to evaluate it |

The methodology chooser links to focused [condition and occurrence](methodologies/SIGNAL_RESEARCH.md), [model-comparison](methodologies/MODEL_RESEARCH.md), [strategy](methodologies/STRATEGY_RESEARCH.md), [robustness](methodologies/ROBUSTNESS_RESEARCH.md) and [predictive](methodologies/PREDICTIVE_RESEARCH.md) method pages. These are methods for framing and evaluating questions; only pages listed as workflows above describe executable orchestration. [Portfolio Research](../../vision/PORTFOLIO_RESEARCH_FUTURE.md) remains a future direction.

Signal Research, Strategy Research and Strategy Execution are independent workflows with shared upstream contracts, not stages of one mandatory pipeline.
