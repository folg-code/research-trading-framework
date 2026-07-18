"""Page-oriented loaders for research, strategy, and robustness artifacts."""

from dashboard_app.views.research import ResearchRunArtifacts, list_research_runs, load_research_run
from dashboard_app.views.robustness import (
    RobustnessExperimentArtifacts,
    list_robustness_experiments,
    load_robustness_experiment,
)
from dashboard_app.views.strategy import (
    StrategyRunArtifacts,
    chart_window_for_trade,
    list_strategy_runs,
    load_strategy_run,
    load_trade_chart_window,
    trades_to_views,
)

__all__ = [
    "ResearchRunArtifacts",
    "RobustnessExperimentArtifacts",
    "StrategyRunArtifacts",
    "chart_window_for_trade",
    "list_research_runs",
    "list_robustness_experiments",
    "list_strategy_runs",
    "load_research_run",
    "load_robustness_experiment",
    "load_strategy_run",
    "load_trade_chart_window",
    "trades_to_views",
]
