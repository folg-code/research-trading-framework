"""Integration-style tests for run_robustness_experiment orchestration."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_parameter_sweep_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    RunRobustnessExperimentRequest,
    run_robustness_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import (
    ExperimentConfigStatus,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import StrategyResearchDatasetRepository
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_run_robustness_experiment_executes_parameter_grid(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-grid-run"
    spec = build_parameter_sweep_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )

    result = run_robustness_experiment(
        RunRobustnessExperimentRequest(
            spec=spec,
            storage_root=storage_root,
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            resume=True,
        )
    )

    assert result.completed_count == 2
    assert result.failed_count == 0
    assert result.skipped_count == 0
    assert len(result.child_run_refs) == 2

    experiment_repo = RobustnessExperimentRepository(storage_root)
    registry = experiment_repo.read_registry(experiment_id)
    assert all(entry.status is ExperimentConfigStatus.COMPLETED for entry in registry.entries)
    assert len(experiment_repo.read_child_runs(experiment_id)) == 2

    strategy_repo = StrategyResearchDatasetRepository(storage_root)
    for run_ref in result.child_run_refs:
        envelope = strategy_repo.read(run_ref)
        assert envelope.manifest.experiment_id == experiment_id


def test_run_robustness_experiment_resumes_completed_cells(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-resume-run"
    spec = build_parameter_sweep_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )
    request = RunRobustnessExperimentRequest(
        spec=spec,
        storage_root=storage_root,
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=requested_range,
        assumptions=SimulationAssumptions(),
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
        resume=True,
    )

    first = run_robustness_experiment(request)
    second = run_robustness_experiment(request)

    assert first.completed_count == 2
    assert second.completed_count == 0
    assert second.skipped_count == 2
    assert second.child_run_refs == first.child_run_refs
