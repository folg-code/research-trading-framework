"""Application orchestration for Strategy Research runs."""

from trading_framework.application.strategy_research.analyze_strategy_research import (
    AnalyzeStrategyResearchError,
    AnalyzeStrategyResearchRequest,
    AnalyzeStrategyResearchResult,
    analyze_strategy_research_run,
)
from trading_framework.application.strategy_research.dashboard import (
    BuildStrategyDashboardRequest,
    build_strategy_dashboard_view_model,
)
from trading_framework.application.strategy_research.entry_signals import build_gated_entry_signals
from trading_framework.application.strategy_research.run_strategy_research import (
    RunStrategyResearchRequest,
    RunStrategyResearchResult,
    StrategyResearchError,
    run_strategy_research,
)
from trading_framework.application.strategy_research.summarize import (
    StrategyRunSummary,
)

__all__ = [
    "AnalyzeStrategyResearchError",
    "AnalyzeStrategyResearchRequest",
    "AnalyzeStrategyResearchResult",
    "BuildStrategyDashboardRequest",
    "RunStrategyResearchRequest",
    "RunStrategyResearchResult",
    "StrategyResearchError",
    "StrategyRunSummary",
    "analyze_strategy_research_run",
    "build_gated_entry_signals",
    "build_strategy_dashboard_view_model",
    "run_strategy_research",
]
