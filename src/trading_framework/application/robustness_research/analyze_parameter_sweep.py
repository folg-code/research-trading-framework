"""Read-only parameter sweep analytics orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from trading_framework.application.strategy_research.summarize import summarize_strategy_run
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import (
    ExperimentConfigStatus,
    ExperimentRegistry,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)
from trading_framework.research.robustness.analytics.parameter_sweep import (
    ParameterSweepAnalytics,
    SweepMetric,
    SweepRunMetrics,
    build_parameter_sweep_analytics,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind


class AnalyzeParameterSweepError(ValidationError):
    """Raised when parameter sweep analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeParameterSweepRequest:
    """Input for read-only parameter sweep analytics."""

    experiment_id: str
    storage_root: Path
    ranking_metric: SweepMetric = SweepMetric.NET_PNL
    stability_threshold: float = 0.7
    isolation_neighbor_ratio: Decimal = Decimal("0.5")
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeParameterSweepResult:
    """Outcome of parameter sweep analytics."""

    analytics: ParameterSweepAnalytics


def analyze_parameter_sweep(
    request: AnalyzeParameterSweepRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeParameterSweepResult:
    """Load completed child runs and compute parameter sweep analytics."""
    if request.stability_threshold < 0 or request.stability_threshold > 1:
        msg = "stability_threshold must be between 0 and 1"
        raise AnalyzeParameterSweepError(msg)
    if request.isolation_neighbor_ratio < 0 or request.isolation_neighbor_ratio > 1:
        msg = "isolation_neighbor_ratio must be between 0 and 1"
        raise AnalyzeParameterSweepError(msg)

    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)

    manifest = experiment_repo.read_manifest(request.experiment_id)
    if RobustnessExperimentKind.PARAMETER_SWEEP not in manifest.spec.kinds:
        msg = "experiment does not declare PARAMETER_SWEEP"
        raise AnalyzeParameterSweepError(msg)
    if manifest.spec.parameter_sweep is None:
        msg = "PARAMETER_SWEEP requires parameter_sweep spec"
        raise AnalyzeParameterSweepError(msg)

    registry = experiment_repo.read_registry(request.experiment_id)
    completed_runs = _load_completed_runs(registry=registry, strategy_repo=strategy_repo)
    analytics = build_parameter_sweep_analytics(
        experiment_id=request.experiment_id,
        parameter_sweep=manifest.spec.parameter_sweep,
        completed_runs=completed_runs,
        ranking_metric=request.ranking_metric,
        stability_threshold=request.stability_threshold,
        isolation_neighbor_ratio=request.isolation_neighbor_ratio,
    )
    if request.persist:
        experiment_repo.write_parameter_sweep_analytics(analytics)
    return AnalyzeParameterSweepResult(analytics=analytics)


def _load_completed_runs(
    *,
    registry: ExperimentRegistry,
    strategy_repo: StrategyResearchDatasetRepository,
) -> tuple[SweepRunMetrics, ...]:
    runs: list[SweepRunMetrics] = []
    for entry in registry.entries:
        if entry.status is not ExperimentConfigStatus.COMPLETED:
            continue
        if entry.strategy_run_id is None:
            continue
        envelope = strategy_repo.read(StrategyResearchRunRef(run_id=entry.strategy_run_id))
        summary = summarize_strategy_run(
            trades=envelope.trades,
            equity=envelope.equity,
        )
        runs.append(
            SweepRunMetrics(
                config_id=entry.config_id,
                config_fingerprint=entry.config_fingerprint,
                parameter_overrides=entry.parameter_overrides,
                strategy_run_id=entry.strategy_run_id,
                summary=summary,
            )
        )
    if not runs:
        msg = "parameter sweep analytics requires at least one completed child run"
        raise AnalyzeParameterSweepError(msg)
    return tuple(runs)
