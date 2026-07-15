"""Run walk-forward robustness experiments — fold execution with train selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.application.strategy_research.summarize import summarize_strategy_run
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import strategy_research_run_dir
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.robustness import (
    ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
    ChildRunRecord,
    ExperimentConfigStatus,
    RobustnessExperimentManifest,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.robustness.analytics.parameter_sweep import (
    SweepMetric,
    SweepRunMetrics,
)
from trading_framework.research.robustness.analytics.walk_forward import select_best_train_config
from trading_framework.research.robustness.experiment import RobustnessExperimentSpec
from trading_framework.research.robustness.grid import expand_parameter_grid
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.strategy_template import build_strategy_model_from_cell
from trading_framework.research.robustness.walk_forward import (
    WalkForwardFold,
    WalkForwardFoldPlan,
    WalkForwardFoldResult,
    WalkForwardResults,
    plan_walk_forward_folds,
    timeframe_bar_step,
)
from trading_framework.research.simulation import (
    SimulationAssumptions,
    simulation_assumptions_fingerprint,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class RunWalkForwardExperimentError(ValidationError):
    """Raised when walk-forward experiment orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunWalkForwardExperimentRequest:
    """Input for one walk-forward experiment execution."""

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
class RunWalkForwardExperimentResult:
    """Outcome of one walk-forward experiment execution pass."""

    experiment_id: str
    results: WalkForwardResults
    completed_fold_count: int
    failed_fold_count: int
    skipped_fold_count: int


def run_walk_forward_experiment(
    request: RunWalkForwardExperimentRequest,
    *,
    repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> RunWalkForwardExperimentResult:
    """Plan folds, select parameters on train only, and evaluate OOS per fold."""
    spec = request.spec
    if spec.dataset_ref != str(request.dataset_ref):
        msg = "spec.dataset_ref must match request.dataset_ref"
        raise RunWalkForwardExperimentError(msg)
    if RobustnessExperimentKind.WALK_FORWARD not in spec.kinds:
        msg = "experiment must declare WALK_FORWARD"
        raise RunWalkForwardExperimentError(msg)
    if spec.walk_forward is None or spec.parameter_sweep is None:
        msg = "WALK_FORWARD requires walk_forward and parameter_sweep specs"
        raise RunWalkForwardExperimentError(msg)

    repo = repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)
    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)
    evaluation_timeframe = (
        Timeframe(spec.evaluation_timeframe)
        if spec.evaluation_timeframe is not None
        else request.evaluation_timeframe
    )

    plan, existing_results = _load_or_initialize_plan(
        repo=repo,
        spec=spec,
        requested_range=request.requested_range,
        assumptions_fingerprint=assumptions_fingerprint,
        resume=request.resume,
    )
    results_by_fold_id = {result.fold.fold_id: result for result in existing_results.folds}

    completed_count = 0
    failed_count = 0
    skipped_count = 0
    updated_results: list[WalkForwardFoldResult] = []

    for fold in plan.folds:
        existing = results_by_fold_id.get(fold.fold_id)
        if existing is not None and existing.status == ExperimentConfigStatus.COMPLETED.value:
            updated_results.append(existing)
            skipped_count += 1
            continue
        if existing is not None and existing.status == ExperimentConfigStatus.FAILED.value:
            if request.resume:
                existing = None
            else:
                updated_results.append(existing)
                failed_count += 1
                continue

        try:
            fold_result = _execute_fold(
                fold=fold,
                spec=spec,
                request=request,
                evaluation_timeframe=evaluation_timeframe,
                strategy_repo=strategy_repo,
                repo=repo,
            )
        except Exception as exc:
            failed_count += 1
            updated_results.append(
                WalkForwardFoldResult(
                    fold=fold,
                    status=ExperimentConfigStatus.FAILED.value,
                    error_message=str(exc),
                )
            )
            continue

        completed_count += 1
        updated_results.append(fold_result)

    final_results = WalkForwardResults(
        experiment_id=spec.experiment_id,
        folds=tuple(updated_results),
    )
    repo.write_walk_forward_results(final_results)

    return RunWalkForwardExperimentResult(
        experiment_id=spec.experiment_id,
        results=final_results,
        completed_fold_count=completed_count,
        failed_fold_count=failed_count,
        skipped_fold_count=skipped_count,
    )


def _load_or_initialize_plan(
    *,
    repo: RobustnessExperimentRepository,
    spec: RobustnessExperimentSpec,
    requested_range: TimeRange,
    assumptions_fingerprint: str,
    resume: bool,
) -> tuple[WalkForwardFoldPlan, WalkForwardResults]:
    if repo.walk_forward_plan_exists(spec.experiment_id):
        if not resume:
            msg = f"experiment already exists: {spec.experiment_id}"
            raise RunWalkForwardExperimentError(msg)
        plan = repo.read_walk_forward_plan(spec.experiment_id)
        try:
            results = repo.read_walk_forward_results(spec.experiment_id)
        except FileNotFoundError:
            results = WalkForwardResults(experiment_id=spec.experiment_id, folds=())
        return plan, results

    assert spec.walk_forward is not None
    bar_step = timeframe_bar_step(spec.timeframe)
    folds = plan_walk_forward_folds(
        overall_range=requested_range,
        spec=spec.walk_forward,
        bar_step=bar_step,
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
    plan = WalkForwardFoldPlan(experiment_id=spec.experiment_id, folds=folds)
    repo.write_walk_forward_plan(plan)
    return plan, WalkForwardResults(experiment_id=spec.experiment_id, folds=())


def _execute_fold(
    *,
    fold: WalkForwardFold,
    spec: RobustnessExperimentSpec,
    request: RunWalkForwardExperimentRequest,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    repo: RobustnessExperimentRepository,
) -> WalkForwardFoldResult:
    assert spec.parameter_sweep is not None
    assert spec.walk_forward is not None
    cells = expand_parameter_grid(spec.parameter_sweep)
    train_runs: list[SweepRunMetrics] = []

    for cell in cells:
        config_id = f"{fold.fold_id}_train_{cell.config_id}"
        run_ref = _execute_strategy_run(
            spec=spec,
            request=request,
            parameter_overrides=cell.parameter_overrides,
            requested_range=fold.train_range,
            config_id=config_id,
            evaluation_timeframe=evaluation_timeframe,
            strategy_repo=strategy_repo,
        )
        envelope = strategy_repo.read(run_ref)
        summary = summarize_strategy_run(trades=envelope.trades, equity=envelope.equity)
        train_runs.append(
            SweepRunMetrics(
                config_id=cell.config_id,
                config_fingerprint=cell.config_fingerprint,
                parameter_overrides=cell.parameter_overrides,
                strategy_run_id=run_ref.run_id,
                summary=summary,
            )
        )
        repo.append_child_run(
            ChildRunRecord(
                experiment_id=spec.experiment_id,
                config_id=config_id,
                config_fingerprint=cell.config_fingerprint,
                strategy_run_id=run_ref.run_id,
                recorded_at_utc=datetime.now(tz=UTC),
            )
        )

    selection = select_best_train_config(
        fold=fold,
        train_runs=tuple(train_runs),
        selection_metric=SweepMetric(spec.walk_forward.selection_metric),
    )
    oos_config_id = f"{fold.fold_id}_oos"
    oos_ref = _execute_strategy_run(
        spec=spec,
        request=request,
        parameter_overrides=selection.parameter_overrides,
        requested_range=fold.oos_range,
        config_id=oos_config_id,
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
    )
    oos_envelope = strategy_repo.read(oos_ref)
    oos_summary = summarize_strategy_run(
        trades=oos_envelope.trades,
        equity=oos_envelope.equity,
    )
    repo.append_child_run(
        ChildRunRecord(
            experiment_id=spec.experiment_id,
            config_id=oos_config_id,
            config_fingerprint=selection.config_id,
            strategy_run_id=oos_ref.run_id,
            recorded_at_utc=datetime.now(tz=UTC),
        )
    )

    return WalkForwardFoldResult(
        fold=fold,
        status=ExperimentConfigStatus.COMPLETED.value,
        selected_config_id=selection.config_id,
        selected_parameter_overrides=selection.parameter_overrides,
        selected_strategy_run_id=selection.strategy_run_id,
        train_net_pnl=str(selection.train_net_pnl),
        oos_strategy_run_id=oos_ref.run_id,
        oos_net_pnl=str(oos_summary.net_pnl),
    )


def _execute_strategy_run(
    *,
    spec: RobustnessExperimentSpec,
    request: RunWalkForwardExperimentRequest,
    parameter_overrides: dict[str, str],
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
        raise RunWalkForwardExperimentError(msg)
    if not hasattr(risk_model, "position_quantity"):
        msg = "strategy risk model must expose position_quantity"
        raise RunWalkForwardExperimentError(msg)

    eval_tf = evaluation_timeframe or request.timeframe
    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)
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
            assumptions=request.assumptions,
            evaluation_timeframe=evaluation_timeframe,
            session_resolver=request.session_resolver,
            experiment_id=spec.experiment_id,
            persist=True,
        ),
        repository=strategy_repo,
    )
    return result.run_ref
