"""Application orchestration for Strategy Research runs."""

from trading_framework.application.strategy_research.entry_signals import build_gated_entry_signals
from trading_framework.application.strategy_research.run_strategy_research import (
    RunStrategyResearchRequest,
    RunStrategyResearchResult,
    StrategyResearchError,
    run_strategy_research,
)

__all__ = [
    "RunStrategyResearchRequest",
    "RunStrategyResearchResult",
    "StrategyResearchError",
    "build_gated_entry_signals",
    "run_strategy_research",
]
