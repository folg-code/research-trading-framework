"""Run Monte Carlo robustness experiments — baseline reference and path simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import strategy_research_run_dir
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.robustness import (
    ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
    ChildRunRecord,
    RobustnessExperimentManifest,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.robustness.analytics.monte_carlo import run_monte_carlo_simulation
from trading_framework.research.robustness.experiment import RobustnessExperimentSpec
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.monte_carlo import MonteCarloResults
from trading_framework.research.robustness.strategy_template import build_strategy_model_from_cell
from trading_framework.research.simulation import (
    SimulationAssumptions,
    simulation_assumptions_fingerprint,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class RunMonteCarloExperimentError(ValidationError):
    """Raised when Monte Carlo experiment orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunMonteCarloExperimentRequest:
    """Input for one Monte Carlo experiment execution."""

    spec: RobustnessExperimentSpec
    storage_root: Path
    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    assumptions: SimulationAssumptions
    evaluation_timeframe: Timeframe | None = None
    session_resolver: TradingSessionResolver | None = None
    resume: bool = True


@dataclass(frozen=True, slots=True)
class RunMonteCarloExperimentResult:
    """Outcome of one Monte Carlo experiment execution pass."""

    experiment_id: str
    results: MonteCarloResults
    skipped: bool


def run_monte_carlo_experiment(
    request: RunMonteCarloExperimentRequest,
    *,
    repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> RunMonteCarloExperimentResult:
    """Run baseline strategy research and simulate trade-level Monte Carlo paths."""
    spec = request.spec
    if spec.dataset_ref != str(request.dataset_ref):
        msg = "spec.dataset_ref must match request.dataset_ref"
        raise RunMonteCarloExperimentError(msg)
    if RobustnessExperimentKind.MONTE_CARLO not in spec.kinds:
        msg = "experiment must declare MONTE_CARLO"
        raise RunMonteCarloExperimentError(msg)
    if spec.monte_carlo is None:
        msg = "MONTE_CARLO requires monte_carlo spec"
        raise RunMonteCarloExperimentError(msg)

    repo = repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)
    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)
    evaluation_timeframe = (
        Timeframe(spec.evaluation_timeframe)
        if spec.evaluation_timeframe is not None
        else request.evaluation_timeframe
    )

    if repo.monte_carlo_results_exist(spec.experiment_id):
        if not request.resume:
            msg = f"experiment already exists: {spec.experiment_id}"
            raise RunMonteCarloExperimentError(msg)
        results = repo.read_monte_carlo_results(spec.experiment_id)
        return RunMonteCarloExperimentResult(
            experiment_id=spec.experiment_id,
            results=results,
            skipped=True,
        )

    manifest = RobustnessExperimentManifest(
        experiment_id=spec.experiment_id,
        schema_version=ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        spec=spec,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
    repo.write_manifest(manifest)

    baseline_ref = _execute_baseline_run(
        spec=spec,
        request=request,
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
        repo=repo,
    )
    baseline_envelope = strategy_repo.read(baseline_ref)
    method_results = run_monte_carlo_simulation(
        trades=baseline_envelope.trades,
        spec=spec.monte_carlo,
        initial_capital=request.assumptions.initial_capital,
    )
    results = MonteCarloResults(
        experiment_id=spec.experiment_id,
        reference_strategy_run_id=baseline_ref.run_id,
        rng_seed=spec.monte_carlo.rng_seed,
        methods=method_results,
    )
    repo.write_monte_carlo_results(results)
    return RunMonteCarloExperimentResult(
        experiment_id=spec.experiment_id,
        results=results,
        skipped=False,
    )


def _execute_baseline_run(
    *,
    spec: RobustnessExperimentSpec,
    request: RunMonteCarloExperimentRequest,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    repo: RobustnessExperimentRepository,
) -> StrategyResearchRunRef:
    assert spec.monte_carlo is not None
    parameter_overrides = spec.monte_carlo.parameter_overrides or {}
    run_ref = _execute_strategy_run(
        spec=spec,
        request=request,
        parameter_overrides=parameter_overrides,
        assumptions=request.assumptions,
        requested_range=request.requested_range,
        config_id="monte_carlo_baseline",
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
    )
    repo.append_child_run(
        ChildRunRecord(
            experiment_id=spec.experiment_id,
            config_id="monte_carlo_baseline",
            config_fingerprint="monte_carlo_baseline",
            strategy_run_id=run_ref.run_id,
            recorded_at_utc=datetime.now(tz=UTC),
        )
    )
    return run_ref


def _execute_strategy_run(
    *,
    spec: RobustnessExperimentSpec,
    request: RunMonteCarloExperimentRequest,
    parameter_overrides: dict[str, str],
    assumptions: SimulationAssumptions,
    requested_range: TimeRange,
    config_id: str,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
) -> StrategyResearchRunRef:
    strategy_model = build_strategy_model_from_cell(
        template_id=spec.strategy_template_id,
        parameter_overrides=parameter_overrides,
    )
    exit_model = strategy_model.exit_model
    risk_model = strategy_model.risk_model
    if not hasattr(exit_model, "exit_after_bars"):
        msg = "strategy exit model must expose exit_after_bars"
        raise RunMonteCarloExperimentError(msg)
    if not hasattr(risk_model, "position_quantity"):
        msg = "strategy risk model must expose position_quantity"
        raise RunMonteCarloExperimentError(msg)

    eval_tf = evaluation_timeframe or request.timeframe
    assumptions_fingerprint = simulation_assumptions_fingerprint(assumptions)
    run_id = derive_strategy_run_id(
        strategy_model_id=strategy_model.strategy_model_id,
        market_model_id=strategy_model.market_model.market_model_id,
        signal_model_id=strategy_model.signal_model.signal_model_id,
        exit_model_id=exit_model.exit_model_id,
        exit_after_bars=int(exit_model.exit_after_bars),
        risk_model_id=risk_model.risk_model_id,
        position_quantity=format(risk_model.position_quantity(), "f"),
        source_dataset_ref=str(request.dataset_ref),
        evaluation_timeframe=eval_tf.value,
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
    run_dir = strategy_research_run_dir(request.storage_root, run_id)
    if run_dir.exists():
        return StrategyResearchRunRef(run_id=run_id)

    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=requested_range,
            storage_root=request.storage_root,
            strategy_model=strategy_model,
            assumptions=assumptions,
            evaluation_timeframe=evaluation_timeframe,
            session_resolver=request.session_resolver,
            experiment_id=spec.experiment_id,
            persist=True,
        ),
        repository=strategy_repo,
    )
    return result.run_ref
