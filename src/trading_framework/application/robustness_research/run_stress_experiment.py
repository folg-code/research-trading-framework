"""Run stress-test robustness experiments — baseline and scenario execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    SharedStrategyEvaluationCache,
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
from trading_framework.research.robustness.analytics.stress import (
    apply_remove_top_days_stress,
    apply_remove_top_trades_stress,
)
from trading_framework.research.robustness.experiment import RobustnessExperimentSpec
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.strategy_template import build_strategy_model_from_cell
from trading_framework.research.robustness.stress import (
    StressScenarioMode,
    StressScenarioResult,
    StressScenarioSpec,
    StressTestResults,
    apply_stress_assumptions,
    apply_stress_strategy_model,
    scenario_fingerprint,
)
from trading_framework.research.simulation import (
    SimulationAssumptions,
    simulation_assumptions_fingerprint,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class RunStressExperimentError(ValidationError):
    """Raised when stress experiment orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunStressExperimentRequest:
    """Input for one stress experiment execution."""

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
class RunStressExperimentResult:
    """Outcome of one stress experiment execution pass."""

    experiment_id: str
    results: StressTestResults
    completed_scenario_count: int
    failed_scenario_count: int
    skipped_scenario_count: int


def run_stress_experiment(
    request: RunStressExperimentRequest,
    *,
    repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> RunStressExperimentResult:
    """Run baseline strategy research and execute declared stress scenarios."""
    spec = request.spec
    if spec.dataset_ref != str(request.dataset_ref):
        msg = "spec.dataset_ref must match request.dataset_ref"
        raise RunStressExperimentError(msg)
    if RobustnessExperimentKind.STRESS_TEST not in spec.kinds:
        msg = "experiment must declare STRESS_TEST"
        raise RunStressExperimentError(msg)
    if spec.stress_test is None:
        msg = "STRESS_TEST requires stress_test spec"
        raise RunStressExperimentError(msg)

    repo = repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)
    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)
    evaluation_timeframe = (
        Timeframe(spec.evaluation_timeframe)
        if spec.evaluation_timeframe is not None
        else request.evaluation_timeframe
    )

    evaluation_cache = SharedStrategyEvaluationCache()
    baseline_run_id, existing_results = _load_or_initialize_stress(
        repo=repo,
        spec=spec,
        request=request,
        assumptions_fingerprint=assumptions_fingerprint,
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
        resume=request.resume,
        evaluation_cache=evaluation_cache,
    )
    baseline_envelope = strategy_repo.read(StrategyResearchRunRef(run_id=baseline_run_id))

    results_by_id = {result.scenario_id: result for result in existing_results.scenarios}
    completed_count = 0
    failed_count = 0
    skipped_count = 0
    updated_results: list[StressScenarioResult] = []

    for scenario in spec.stress_test.scenarios:
        existing = results_by_id.get(scenario.scenario_id)
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
            scenario_result = _execute_scenario(
                scenario=scenario,
                spec=spec,
                request=request,
                evaluation_timeframe=evaluation_timeframe,
                strategy_repo=strategy_repo,
                repo=repo,
                baseline_envelope=baseline_envelope,
                evaluation_cache=evaluation_cache,
            )
        except Exception as exc:
            failed_count += 1
            updated_results.append(
                StressScenarioResult(
                    scenario_id=scenario.scenario_id,
                    scenario_fingerprint=scenario_fingerprint(scenario),
                    mode=scenario.mode().value,
                    status=ExperimentConfigStatus.FAILED.value,
                    error_message=str(exc),
                )
            )
            continue

        completed_count += 1
        updated_results.append(scenario_result)

    final_results = StressTestResults(
        experiment_id=spec.experiment_id,
        baseline_strategy_run_id=baseline_run_id,
        scenarios=tuple(updated_results),
    )
    repo.write_stress_results(final_results)

    return RunStressExperimentResult(
        experiment_id=spec.experiment_id,
        results=final_results,
        completed_scenario_count=completed_count,
        failed_scenario_count=failed_count,
        skipped_scenario_count=skipped_count,
    )


def _load_or_initialize_stress(
    *,
    repo: RobustnessExperimentRepository,
    spec: RobustnessExperimentSpec,
    request: RunStressExperimentRequest,
    assumptions_fingerprint: str,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    resume: bool,
    evaluation_cache: SharedStrategyEvaluationCache,
) -> tuple[str, StressTestResults]:
    if repo.stress_results_exist(spec.experiment_id):
        if not resume:
            msg = f"experiment already exists: {spec.experiment_id}"
            raise RunStressExperimentError(msg)
        results = repo.read_stress_results(spec.experiment_id)
        return results.baseline_strategy_run_id, results

    assert spec.stress_test is not None
    manifest = RobustnessExperimentManifest(
        experiment_id=spec.experiment_id,
        schema_version=ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        spec=spec,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
    if not repo.manifest_exists(spec.experiment_id):
        repo.write_manifest(manifest)

    baseline_ref = _execute_baseline_run(
        spec=spec,
        request=request,
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
        repo=repo,
        evaluation_cache=evaluation_cache,
    )
    return baseline_ref.run_id, StressTestResults(
        experiment_id=spec.experiment_id,
        baseline_strategy_run_id=baseline_ref.run_id,
        scenarios=(),
    )


def _execute_baseline_run(
    *,
    spec: RobustnessExperimentSpec,
    request: RunStressExperimentRequest,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    repo: RobustnessExperimentRepository,
    evaluation_cache: SharedStrategyEvaluationCache,
) -> StrategyResearchRunRef:
    assert spec.stress_test is not None
    parameter_overrides = spec.stress_test.parameter_overrides or {}
    run_ref = _execute_strategy_run(
        spec=spec,
        request=request,
        parameter_overrides=parameter_overrides,
        assumptions=request.assumptions,
        strategy_model=None,
        requested_range=request.requested_range,
        config_id="baseline",
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
        evaluation_cache=evaluation_cache,
    )
    repo.append_child_run(
        ChildRunRecord(
            experiment_id=spec.experiment_id,
            config_id="baseline",
            config_fingerprint="baseline",
            strategy_run_id=run_ref.run_id,
            recorded_at_utc=datetime.now(tz=UTC),
        )
    )
    return run_ref


def _execute_scenario(
    *,
    scenario: StressScenarioSpec,
    spec: RobustnessExperimentSpec,
    request: RunStressExperimentRequest,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    repo: RobustnessExperimentRepository,
    baseline_envelope: object,
    evaluation_cache: SharedStrategyEvaluationCache,
) -> StressScenarioResult:
    from trading_framework.research.datasets.strategy_research import StrategyResearchRunEnvelope

    if not isinstance(baseline_envelope, StrategyResearchRunEnvelope):
        msg = "baseline envelope must be StrategyResearchRunEnvelope"
        raise RunStressExperimentError(msg)

    fingerprint = scenario_fingerprint(scenario)
    config_id = f"stress_{scenario.scenario_id}"

    if scenario.mode() is StressScenarioMode.POST_PROCESS:
        if scenario.remove_top_n_trades > 0:
            _, _, summary = apply_remove_top_trades_stress(
                trades=baseline_envelope.trades,
                equity=baseline_envelope.equity,
                scenario=scenario,
                initial_capital=request.assumptions.initial_capital,
            )
        else:
            _, _, summary = apply_remove_top_days_stress(
                trades=baseline_envelope.trades,
                equity=baseline_envelope.equity,
                scenario=scenario,
                initial_capital=request.assumptions.initial_capital,
            )
        return StressScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_fingerprint=fingerprint,
            mode=scenario.mode().value,
            status=ExperimentConfigStatus.COMPLETED.value,
            strategy_run_id=baseline_envelope.manifest.run_id,
            net_pnl=str(summary.net_pnl),
            trade_count=summary.trade_count,
        )

    stressed_assumptions = apply_stress_assumptions(request.assumptions, scenario)
    assert spec.stress_test is not None
    parameter_overrides = spec.stress_test.parameter_overrides or {}
    base_strategy = build_strategy_model_from_cell(
        template_id=spec.strategy_template_id,
        parameter_overrides=parameter_overrides,
    )
    stressed_strategy = apply_stress_strategy_model(base_strategy, scenario)
    run_ref = _execute_strategy_run(
        spec=spec,
        request=request,
        parameter_overrides=parameter_overrides,
        assumptions=stressed_assumptions,
        strategy_model=stressed_strategy,
        requested_range=request.requested_range,
        config_id=config_id,
        evaluation_timeframe=evaluation_timeframe,
        strategy_repo=strategy_repo,
        evaluation_cache=evaluation_cache,
    )
    envelope = strategy_repo.read(run_ref)
    summary = summarize_strategy_run(trades=envelope.trades, equity=envelope.equity)
    repo.append_child_run(
        ChildRunRecord(
            experiment_id=spec.experiment_id,
            config_id=config_id,
            config_fingerprint=fingerprint,
            strategy_run_id=run_ref.run_id,
            recorded_at_utc=datetime.now(tz=UTC),
        )
    )
    return StressScenarioResult(
        scenario_id=scenario.scenario_id,
        scenario_fingerprint=fingerprint,
        mode=scenario.mode().value,
        status=ExperimentConfigStatus.COMPLETED.value,
        strategy_run_id=run_ref.run_id,
        net_pnl=str(summary.net_pnl),
        trade_count=summary.trade_count,
    )


def _execute_strategy_run(
    *,
    spec: RobustnessExperimentSpec,
    request: RunStressExperimentRequest,
    parameter_overrides: dict[str, str],
    assumptions: SimulationAssumptions,
    strategy_model: object | None,
    requested_range: TimeRange,
    config_id: str,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
    evaluation_cache: SharedStrategyEvaluationCache,
) -> StrategyResearchRunRef:
    resolved_strategy = strategy_model or build_strategy_model_from_cell(
        template_id=spec.strategy_template_id,
        parameter_overrides=parameter_overrides,
    )
    from trading_framework.strategy.strategy_model import StrategyModelDefinition

    if not isinstance(resolved_strategy, StrategyModelDefinition):
        msg = "strategy model must be StrategyModelDefinition"
        raise RunStressExperimentError(msg)

    exit_model = resolved_strategy.exit_model
    risk_model = resolved_strategy.risk_model
    if not hasattr(exit_model, "exit_after_bars"):
        msg = "strategy exit model must expose exit_after_bars"
        raise RunStressExperimentError(msg)
    if not hasattr(risk_model, "position_quantity"):
        msg = "strategy risk model must expose position_quantity"
        raise RunStressExperimentError(msg)

    eval_tf = evaluation_timeframe or request.timeframe
    assumptions_fingerprint = simulation_assumptions_fingerprint(assumptions)
    run_id = derive_strategy_run_id(
        strategy_model_id=resolved_strategy.strategy_model_id,
        market_model_id=resolved_strategy.market_model.market_model_id,
        signal_model_id=resolved_strategy.signal_model.signal_model_id,
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

    shared_evaluation = evaluation_cache.get_or_build(
        dataset_ref=request.dataset_ref,
        timeframe=request.timeframe,
        requested_range=requested_range,
        storage_root=request.storage_root,
        strategy_model=resolved_strategy,
        evaluation_timeframe=evaluation_timeframe,
        session_resolver=request.session_resolver,
    )
    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=requested_range,
            storage_root=request.storage_root,
            strategy_model=resolved_strategy,
            assumptions=assumptions,
            evaluation_timeframe=evaluation_timeframe,
            session_resolver=request.session_resolver,
            experiment_id=spec.experiment_id,
            persist=True,
            shared_evaluation=shared_evaluation,
        ),
        repository=strategy_repo,
    )
    return result.run_ref
