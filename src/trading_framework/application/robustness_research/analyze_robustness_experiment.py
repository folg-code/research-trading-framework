"""Read-only robustness experiment analytics orchestration and verdict."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.robustness_research.analyze_diagnostics_experiment import (
    AnalyzeDiagnosticsExperimentRequest,
    analyze_diagnostics_experiment,
)
from trading_framework.application.robustness_research.analyze_monte_carlo_experiment import (
    AnalyzeMonteCarloExperimentRequest,
    analyze_monte_carlo_experiment,
)
from trading_framework.application.robustness_research.analyze_parameter_sweep import (
    AnalyzeParameterSweepRequest,
    analyze_parameter_sweep,
)
from trading_framework.application.robustness_research.analyze_stress_experiment import (
    AnalyzeStressExperimentRequest,
    analyze_stress_experiment,
)
from trading_framework.application.robustness_research.analyze_walk_forward import (
    AnalyzeWalkForwardRequest,
    analyze_walk_forward,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.datasets.strategy_research import StrategyResearchDatasetRepository
from trading_framework.research.robustness.analytics.diagnostics import (
    StatisticalDiagnosticsAnalytics,
)
from trading_framework.research.robustness.analytics.monte_carlo import MonteCarloAnalytics
from trading_framework.research.robustness.analytics.parameter_sweep import ParameterSweepAnalytics
from trading_framework.research.robustness.analytics.stress import StressTestAnalytics
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardAnalytics
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.report import (
    RobustnessReportViewModel,
    build_robustness_report_view_model,
)
from trading_framework.research.robustness.verdict import (
    RobustnessVerdict,
    VerdictEvaluationContext,
    evaluate_robustness_verdict,
)


class AnalyzeRobustnessExperimentError(ValidationError):
    """Raised when robustness analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeRobustnessExperimentRequest:
    """Input for full experiment analytics and verdict evaluation."""

    experiment_id: str
    storage_root: Path
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeRobustnessExperimentResult:
    """Outcome of full experiment analytics."""

    verdict: RobustnessVerdict
    report_view_model: RobustnessReportViewModel


def analyze_robustness_experiment(
    request: AnalyzeRobustnessExperimentRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeRobustnessExperimentResult:
    """Run kind-specific analytics, evaluate verdict, and bundle report view model."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)
    manifest = experiment_repo.read_manifest(request.experiment_id)
    spec = manifest.spec

    parameter_sweep = _analyze_parameter_sweep_if_needed(
        experiment_id=request.experiment_id,
        storage_root=request.storage_root,
        spec_kinds=spec.kinds,
        persist=request.persist,
        experiment_repo=experiment_repo,
        strategy_repo=strategy_repo,
    )
    walk_forward = _analyze_walk_forward_if_needed(
        experiment_id=request.experiment_id,
        storage_root=request.storage_root,
        spec_kinds=spec.kinds,
        persist=request.persist,
        experiment_repo=experiment_repo,
        strategy_repo=strategy_repo,
    )
    stress = _analyze_stress_if_needed(
        experiment_id=request.experiment_id,
        storage_root=request.storage_root,
        spec_kinds=spec.kinds,
        persist=request.persist,
        experiment_repo=experiment_repo,
        strategy_repo=strategy_repo,
    )
    monte_carlo = _analyze_monte_carlo_if_needed(
        experiment_id=request.experiment_id,
        storage_root=request.storage_root,
        spec_kinds=spec.kinds,
        persist=request.persist,
        experiment_repo=experiment_repo,
    )
    diagnostics = _analyze_diagnostics_if_needed(
        experiment_id=request.experiment_id,
        storage_root=request.storage_root,
        spec_kinds=spec.kinds,
        persist=request.persist,
        experiment_repo=experiment_repo,
        strategy_repo=strategy_repo,
    )

    verdict = evaluate_robustness_verdict(
        experiment_id=request.experiment_id,
        assumptions_fingerprint=manifest.simulation_assumptions_fingerprint,
        thresholds=spec.verdict_thresholds,
        context=VerdictEvaluationContext(
            parameter_sweep=parameter_sweep,
            walk_forward=walk_forward,
            stress=stress,
            monte_carlo=monte_carlo,
            diagnostics=diagnostics,
        ),
    )
    report_view_model = build_robustness_report_view_model(
        experiment_id=request.experiment_id,
        kinds=tuple(kind.value for kind in spec.kinds),
        dataset_ref=spec.dataset_ref,
        strategy_template_id=spec.strategy_template_id,
        timeframe=spec.timeframe,
        framework_version=manifest.framework_version,
        simulation_assumptions_fingerprint=manifest.simulation_assumptions_fingerprint,
        verdict=verdict,
        verdict_thresholds=spec.verdict_thresholds,
        parameter_sweep=parameter_sweep,
        walk_forward=walk_forward,
        stress=stress,
        monte_carlo=monte_carlo,
        diagnostics=diagnostics,
    )
    if request.persist:
        experiment_repo.write_verdict(verdict)
        experiment_repo.write_report_view_model(report_view_model)
    return AnalyzeRobustnessExperimentResult(
        verdict=verdict,
        report_view_model=report_view_model,
    )


def _analyze_parameter_sweep_if_needed(
    *,
    experiment_id: str,
    storage_root: Path,
    spec_kinds: tuple[RobustnessExperimentKind, ...],
    persist: bool,
    experiment_repo: RobustnessExperimentRepository,
    strategy_repo: StrategyResearchDatasetRepository,
) -> ParameterSweepAnalytics | None:
    if RobustnessExperimentKind.PARAMETER_SWEEP not in spec_kinds:
        return None
    if experiment_repo.parameter_sweep_analytics_exists(experiment_id):
        return experiment_repo.read_parameter_sweep_analytics(experiment_id)
    return analyze_parameter_sweep(
        AnalyzeParameterSweepRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            persist=persist,
        ),
        experiment_repository=experiment_repo,
        strategy_repository=strategy_repo,
    ).analytics


def _analyze_walk_forward_if_needed(
    *,
    experiment_id: str,
    storage_root: Path,
    spec_kinds: tuple[RobustnessExperimentKind, ...],
    persist: bool,
    experiment_repo: RobustnessExperimentRepository,
    strategy_repo: StrategyResearchDatasetRepository,
) -> WalkForwardAnalytics | None:
    if RobustnessExperimentKind.WALK_FORWARD not in spec_kinds:
        return None
    try:
        return experiment_repo.read_walk_forward_analytics(experiment_id)
    except FileNotFoundError:
        pass
    return analyze_walk_forward(
        AnalyzeWalkForwardRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            persist=persist,
        ),
        experiment_repository=experiment_repo,
        strategy_repository=strategy_repo,
    ).analytics


def _analyze_stress_if_needed(
    *,
    experiment_id: str,
    storage_root: Path,
    spec_kinds: tuple[RobustnessExperimentKind, ...],
    persist: bool,
    experiment_repo: RobustnessExperimentRepository,
    strategy_repo: StrategyResearchDatasetRepository,
) -> StressTestAnalytics | None:
    if RobustnessExperimentKind.STRESS_TEST not in spec_kinds:
        return None
    if experiment_repo.stress_results_exist(experiment_id):
        try:
            return experiment_repo.read_stress_analytics(experiment_id)
        except FileNotFoundError:
            pass
    return analyze_stress_experiment(
        AnalyzeStressExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            persist=persist,
        ),
        experiment_repository=experiment_repo,
        strategy_repository=strategy_repo,
    ).analytics


def _analyze_monte_carlo_if_needed(
    *,
    experiment_id: str,
    storage_root: Path,
    spec_kinds: tuple[RobustnessExperimentKind, ...],
    persist: bool,
    experiment_repo: RobustnessExperimentRepository,
) -> MonteCarloAnalytics | None:
    if RobustnessExperimentKind.MONTE_CARLO not in spec_kinds:
        return None
    if experiment_repo.monte_carlo_results_exist(experiment_id):
        try:
            return experiment_repo.read_monte_carlo_analytics(experiment_id)
        except FileNotFoundError:
            pass
    return analyze_monte_carlo_experiment(
        AnalyzeMonteCarloExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            persist=persist,
        ),
        experiment_repository=experiment_repo,
    ).analytics


def _analyze_diagnostics_if_needed(
    *,
    experiment_id: str,
    storage_root: Path,
    spec_kinds: tuple[RobustnessExperimentKind, ...],
    persist: bool,
    experiment_repo: RobustnessExperimentRepository,
    strategy_repo: StrategyResearchDatasetRepository,
) -> StatisticalDiagnosticsAnalytics | None:
    if RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS not in spec_kinds:
        return None
    try:
        return experiment_repo.read_diagnostics_analytics(experiment_id)
    except FileNotFoundError:
        pass
    return analyze_diagnostics_experiment(
        AnalyzeDiagnosticsExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            persist=persist,
        ),
        experiment_repository=experiment_repo,
        strategy_repository=strategy_repo,
    ).analytics
