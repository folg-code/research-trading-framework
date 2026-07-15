"""Run a robustness experiment — grid expansion, batch strategy research, resume."""

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
    ExperimentConfigStatus,
    ExperimentRegistry,
    ExperimentRegistryEntry,
    RobustnessExperimentManifest,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.robustness.experiment import RobustnessExperimentSpec
from trading_framework.research.robustness.grid import expand_parameter_grid
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.strategy_template import build_strategy_model_from_cell
from trading_framework.research.simulation import (
    SimulationAssumptions,
    simulation_assumptions_fingerprint,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class RobustnessResearchError(ValidationError):
    """Raised when robustness experiment orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunRobustnessExperimentRequest:
    """Input for one robustness experiment batch execution."""

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
class RunRobustnessExperimentResult:
    """Outcome of one robustness experiment execution pass."""

    experiment_id: str
    registry: ExperimentRegistry
    completed_count: int
    failed_count: int
    skipped_count: int
    child_run_refs: tuple[StrategyResearchRunRef, ...]


def run_robustness_experiment(
    request: RunRobustnessExperimentRequest,
    *,
    repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> RunRobustnessExperimentResult:
    """Expand parameter grid, execute child Strategy Research runs, and update registry."""
    spec = request.spec
    if spec.dataset_ref != str(request.dataset_ref):
        msg = "spec.dataset_ref must match request.dataset_ref"
        raise RobustnessResearchError(msg)

    repo = repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)
    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)

    registry = _load_or_initialize_registry(
        repo=repo,
        spec=spec,
        assumptions_fingerprint=assumptions_fingerprint,
        resume=request.resume,
    )

    evaluation_timeframe = (
        Timeframe(spec.evaluation_timeframe)
        if spec.evaluation_timeframe is not None
        else request.evaluation_timeframe
    )

    completed_count = 0
    failed_count = 0
    skipped_count = 0
    child_run_refs: list[StrategyResearchRunRef] = []
    updated_entries: list[ExperimentRegistryEntry] = []

    for entry in registry.entries:
        if entry.status is ExperimentConfigStatus.COMPLETED:
            updated_entries.append(entry)
            if entry.strategy_run_id is not None:
                child_run_refs.append(StrategyResearchRunRef(run_id=entry.strategy_run_id))
            skipped_count += 1
            continue

        if entry.status is ExperimentConfigStatus.FAILED and not request.resume:
            updated_entries.append(entry)
            failed_count += 1
            continue

        if entry.status is ExperimentConfigStatus.FAILED and request.resume:
            entry = ExperimentRegistryEntry(
                config_id=entry.config_id,
                config_fingerprint=entry.config_fingerprint,
                parameter_overrides=entry.parameter_overrides,
                status=ExperimentConfigStatus.PENDING,
            )

        try:
            run_ref = _execute_config_cell(
                entry=entry,
                spec=spec,
                request=request,
                evaluation_timeframe=evaluation_timeframe,
                strategy_repo=strategy_repo,
            )
        except Exception as exc:
            failed_count += 1
            updated_entries.append(
                ExperimentRegistryEntry(
                    config_id=entry.config_id,
                    config_fingerprint=entry.config_fingerprint,
                    parameter_overrides=entry.parameter_overrides,
                    status=ExperimentConfigStatus.FAILED,
                    error_message=str(exc),
                )
            )
            continue

        completed_count += 1
        updated_entries.append(
            ExperimentRegistryEntry(
                config_id=entry.config_id,
                config_fingerprint=entry.config_fingerprint,
                parameter_overrides=entry.parameter_overrides,
                status=ExperimentConfigStatus.COMPLETED,
                strategy_run_id=run_ref.run_id,
            )
        )
        child_run_refs.append(run_ref)
        repo.append_child_run(
            ChildRunRecord(
                experiment_id=spec.experiment_id,
                config_id=entry.config_id,
                config_fingerprint=entry.config_fingerprint,
                strategy_run_id=run_ref.run_id,
                recorded_at_utc=datetime.now(tz=UTC),
            )
        )

    next_pending_index = _next_pending_index(updated_entries)
    final_registry = ExperimentRegistry(
        experiment_id=spec.experiment_id,
        entries=tuple(updated_entries),
        next_pending_index=next_pending_index,
    )
    repo.write_registry(final_registry)

    return RunRobustnessExperimentResult(
        experiment_id=spec.experiment_id,
        registry=final_registry,
        completed_count=completed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        child_run_refs=tuple(child_run_refs),
    )


def _load_or_initialize_registry(
    *,
    repo: RobustnessExperimentRepository,
    spec: RobustnessExperimentSpec,
    assumptions_fingerprint: str,
    resume: bool,
) -> ExperimentRegistry:
    if repo.manifest_exists(spec.experiment_id):
        if not resume:
            msg = f"experiment already exists: {spec.experiment_id}"
            raise RobustnessResearchError(msg)
        return repo.read_registry(spec.experiment_id)

    if RobustnessExperimentKind.PARAMETER_SWEEP not in spec.kinds:
        msg = "wave 1 requires PARAMETER_SWEEP kind"
        raise RobustnessResearchError(msg)
    if spec.parameter_sweep is None:
        msg = "PARAMETER_SWEEP requires parameter_sweep spec"
        raise RobustnessResearchError(msg)

    cells = expand_parameter_grid(spec.parameter_sweep)
    manifest = RobustnessExperimentManifest(
        experiment_id=spec.experiment_id,
        schema_version=ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        spec=spec,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
    repo.write_manifest(manifest)
    entries = tuple(
        ExperimentRegistryEntry(
            config_id=cell.config_id,
            config_fingerprint=cell.config_fingerprint,
            parameter_overrides=cell.parameter_overrides,
            status=ExperimentConfigStatus.PENDING,
        )
        for cell in cells
    )
    registry = ExperimentRegistry(
        experiment_id=spec.experiment_id,
        entries=entries,
        next_pending_index=0,
    )
    repo.write_registry(registry)
    return registry


def _execute_config_cell(
    *,
    entry: ExperimentRegistryEntry,
    spec: RobustnessExperimentSpec,
    request: RunRobustnessExperimentRequest,
    evaluation_timeframe: Timeframe | None,
    strategy_repo: StrategyResearchDatasetRepository,
) -> StrategyResearchRunRef:
    strategy_model = build_strategy_model_from_cell(
        template_id=spec.strategy_template_id,
        parameter_overrides=entry.parameter_overrides,
    )
    exit_model = strategy_model.exit_model
    risk_model = strategy_model.risk_model
    if not hasattr(exit_model, "exit_after_bars"):
        msg = "strategy exit model must expose exit_after_bars"
        raise RobustnessResearchError(msg)
    if not hasattr(risk_model, "position_quantity"):
        msg = "strategy risk model must expose position_quantity"
        raise RobustnessResearchError(msg)

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
        requested_range_start=request.requested_range.start,
        requested_range_end=request.requested_range.end,
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
            requested_range=request.requested_range,
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


def _next_pending_index(entries: list[ExperimentRegistryEntry]) -> int:
    for index, entry in enumerate(entries):
        if entry.status is ExperimentConfigStatus.PENDING:
            return index
    return len(entries)
