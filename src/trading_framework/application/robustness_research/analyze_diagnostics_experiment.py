"""Read-only statistical diagnostics orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.robustness.analytics.diagnostics import (
    StatisticalDiagnosticsAnalytics,
    build_statistical_diagnostics_analytics,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.strategy_template import build_strategy_model_from_cell


class AnalyzeDiagnosticsExperimentError(ValidationError):
    """Raised when statistical diagnostics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeDiagnosticsExperimentRequest:
    """Input for read-only statistical diagnostics analytics."""

    experiment_id: str
    storage_root: Path
    persist: bool = True
    link_walk_forward: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeDiagnosticsExperimentResult:
    """Outcome of statistical diagnostics analytics."""

    analytics: StatisticalDiagnosticsAnalytics


def analyze_diagnostics_experiment(
    request: AnalyzeDiagnosticsExperimentRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeDiagnosticsExperimentResult:
    """Compute temporal stability, PnL concentration, and optional IS/OOS degradation."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)

    manifest = experiment_repo.read_manifest(request.experiment_id)
    if RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS not in manifest.spec.kinds:
        msg = "experiment does not declare STATISTICAL_DIAGNOSTICS"
        raise AnalyzeDiagnosticsExperimentError(msg)
    if manifest.spec.statistical_diagnostics is None:
        msg = "STATISTICAL_DIAGNOSTICS requires statistical_diagnostics spec"
        raise AnalyzeDiagnosticsExperimentError(msg)

    diagnostics_spec = manifest.spec.statistical_diagnostics
    reference_run_id = _resolve_reference_run_id(
        spec=manifest.spec,
        assumptions_fingerprint=manifest.simulation_assumptions_fingerprint,
        strategy_repo=strategy_repo,
        experiment_repo=experiment_repo,
    )
    envelope = strategy_repo.read(StrategyResearchRunRef(run_id=reference_run_id))

    fold_evaluations = None
    if request.link_walk_forward and RobustnessExperimentKind.WALK_FORWARD in manifest.spec.kinds:
        try:
            walk_forward_analytics = experiment_repo.read_walk_forward_analytics(
                request.experiment_id
            )
            fold_evaluations = walk_forward_analytics.fold_evaluations
        except FileNotFoundError:
            fold_evaluations = None

    analytics = build_statistical_diagnostics_analytics(
        experiment_id=request.experiment_id,
        reference_strategy_run_id=reference_run_id,
        trades=envelope.trades,
        spec=diagnostics_spec,
        fold_evaluations=fold_evaluations,
    )
    if request.persist:
        experiment_repo.write_diagnostics_analytics(analytics)
    return AnalyzeDiagnosticsExperimentResult(analytics=analytics)


def _resolve_reference_run_id(
    *,
    spec: object,
    assumptions_fingerprint: str,
    strategy_repo: StrategyResearchDatasetRepository,
    experiment_repo: RobustnessExperimentRepository,
) -> str:
    from trading_framework.research.robustness.experiment import RobustnessExperimentSpec

    if not isinstance(spec, RobustnessExperimentSpec):
        msg = "manifest spec must be RobustnessExperimentSpec"
        raise AnalyzeDiagnosticsExperimentError(msg)
    if spec.statistical_diagnostics is None:
        msg = "STATISTICAL_DIAGNOSTICS requires statistical_diagnostics spec"
        raise AnalyzeDiagnosticsExperimentError(msg)

    if experiment_repo.monte_carlo_results_exist(spec.experiment_id):
        return experiment_repo.read_monte_carlo_results(
            spec.experiment_id
        ).reference_strategy_run_id
    if experiment_repo.stress_results_exist(spec.experiment_id):
        return experiment_repo.read_stress_results(spec.experiment_id).baseline_strategy_run_id

    parameter_overrides = spec.statistical_diagnostics.parameter_overrides or {}
    strategy_model = build_strategy_model_from_cell(
        template_id=spec.strategy_template_id,
        parameter_overrides=parameter_overrides,
    )
    exit_model = strategy_model.exit_model
    risk_model = strategy_model.risk_model
    if not hasattr(exit_model, "exit_after_bars"):
        msg = "strategy exit model must expose exit_after_bars"
        raise AnalyzeDiagnosticsExperimentError(msg)
    if not hasattr(risk_model, "position_quantity"):
        msg = "strategy risk model must expose position_quantity"
        raise AnalyzeDiagnosticsExperimentError(msg)

    evaluation_timeframe = spec.evaluation_timeframe or spec.timeframe
    return derive_strategy_run_id(
        strategy_model_id=strategy_model.strategy_model_id,
        market_model_id=strategy_model.market_model.market_model_id,
        signal_model_id=strategy_model.signal_model.signal_model_id,
        exit_model_id=exit_model.exit_model_id,
        exit_after_bars=int(exit_model.exit_after_bars),
        risk_model_id=risk_model.risk_model_id,
        position_quantity=format(risk_model.position_quantity(), "f"),
        source_dataset_ref=spec.dataset_ref,
        evaluation_timeframe=evaluation_timeframe,
        requested_range_start=spec.requested_range_start,
        requested_range_end=spec.requested_range_end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
