"""Read-only Monte Carlo experiment analytics orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.robustness.analytics.monte_carlo import (
    MonteCarloAnalytics,
    build_monte_carlo_analytics,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind


class AnalyzeMonteCarloExperimentError(ValidationError):
    """Raised when Monte Carlo analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeMonteCarloExperimentRequest:
    """Input for read-only Monte Carlo analytics."""

    experiment_id: str
    storage_root: Path
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeMonteCarloExperimentResult:
    """Outcome of Monte Carlo analytics."""

    analytics: MonteCarloAnalytics


def analyze_monte_carlo_experiment(
    request: AnalyzeMonteCarloExperimentRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
) -> AnalyzeMonteCarloExperimentResult:
    """Load Monte Carlo results and build envelope and tail probability analytics."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)

    manifest = experiment_repo.read_manifest(request.experiment_id)
    if RobustnessExperimentKind.MONTE_CARLO not in manifest.spec.kinds:
        msg = "experiment does not declare MONTE_CARLO"
        raise AnalyzeMonteCarloExperimentError(msg)
    if manifest.spec.monte_carlo is None:
        msg = "MONTE_CARLO requires monte_carlo spec"
        raise AnalyzeMonteCarloExperimentError(msg)

    results = experiment_repo.read_monte_carlo_results(request.experiment_id)
    analytics = build_monte_carlo_analytics(
        experiment_id=request.experiment_id,
        results=results,
        max_drawdown_threshold=manifest.spec.monte_carlo.max_drawdown_threshold,
    )
    if request.persist:
        experiment_repo.write_monte_carlo_analytics(analytics)
    return AnalyzeMonteCarloExperimentResult(analytics=analytics)
