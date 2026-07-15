"""Read-only stress experiment analytics orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.strategy_research.summarize import summarize_strategy_run
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)
from trading_framework.research.robustness.analytics.stress import (
    StressTestAnalytics,
    build_stress_comparison_table,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind


class AnalyzeStressExperimentError(ValidationError):
    """Raised when stress analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeStressExperimentRequest:
    """Input for read-only stress comparison analytics."""

    experiment_id: str
    storage_root: Path
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeStressExperimentResult:
    """Outcome of stress comparison analytics."""

    analytics: StressTestAnalytics


def analyze_stress_experiment(
    request: AnalyzeStressExperimentRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeStressExperimentResult:
    """Load stress results and build baseline-vs-scenario comparison table."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)

    manifest = experiment_repo.read_manifest(request.experiment_id)
    if RobustnessExperimentKind.STRESS_TEST not in manifest.spec.kinds:
        msg = "experiment does not declare STRESS_TEST"
        raise AnalyzeStressExperimentError(msg)

    stress_results = experiment_repo.read_stress_results(request.experiment_id)
    baseline_envelope = strategy_repo.read(
        StrategyResearchRunRef(run_id=stress_results.baseline_strategy_run_id)
    )
    baseline_summary = summarize_strategy_run(
        trades=baseline_envelope.trades,
        equity=baseline_envelope.equity,
    )
    analytics = build_stress_comparison_table(
        experiment_id=request.experiment_id,
        baseline_summary=baseline_summary,
        baseline_strategy_run_id=stress_results.baseline_strategy_run_id,
        scenario_results=stress_results.scenarios,
    )
    if request.persist:
        experiment_repo.write_stress_analytics(analytics)
    return AnalyzeStressExperimentResult(analytics=analytics)
