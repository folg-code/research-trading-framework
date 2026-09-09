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
from trading_framework.application.strategy_research.resolve_score_condition import (
    ResolvedScoreCondition,
    ScoreConditionFamilyRefusedError,
    ScoreConditionNotFoundError,
    ScoreConditionResolutionError,
    resolve_score_condition,
)
from trading_framework.application.strategy_research.run_strategy_research import (
    RunStrategyResearchRequest,
    RunStrategyResearchResult,
    StrategyResearchError,
    run_strategy_research,
)
from trading_framework.application.strategy_research.shared_evaluation import (
    SharedStrategyEvaluationCache,
    SharedStrategyEvaluationContext,
    SharedStrategyEvaluationError,
    build_shared_strategy_evaluation_context,
)
from trading_framework.application.strategy_research.summarize import (
    StrategyRunSummary,
)

__all__ = [
    "AnalyzeStrategyResearchError",
    "AnalyzeStrategyResearchRequest",
    "AnalyzeStrategyResearchResult",
    "BuildStrategyDashboardRequest",
    "ResolvedScoreCondition",
    "RunStrategyResearchRequest",
    "RunStrategyResearchResult",
    "ScoreConditionFamilyRefusedError",
    "ScoreConditionNotFoundError",
    "ScoreConditionResolutionError",
    "SharedStrategyEvaluationCache",
    "SharedStrategyEvaluationContext",
    "SharedStrategyEvaluationError",
    "StrategyResearchError",
    "StrategyRunSummary",
    "analyze_strategy_research_run",
    "build_gated_entry_signals",
    "build_shared_strategy_evaluation_context",
    "build_strategy_dashboard_view_model",
    "resolve_score_condition",
    "run_strategy_research",
]
