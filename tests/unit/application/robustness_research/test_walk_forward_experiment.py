"""Integration-style tests for walk-forward robustness orchestration."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_walk_forward_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    AnalyzeWalkForwardRequest,
    RunWalkForwardExperimentRequest,
    analyze_walk_forward,
    run_walk_forward_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_run_and_analyze_walk_forward_experiment(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-walk-forward"
    spec = build_walk_forward_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )

    run_result = run_walk_forward_experiment(
        RunWalkForwardExperimentRequest(
            spec=spec,
            storage_root=storage_root,
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    )

    assert run_result.completed_fold_count >= 1
    assert len(run_result.results.folds) >= 1

    analyze_result = analyze_walk_forward(
        AnalyzeWalkForwardRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
        )
    )

    assert len(analyze_result.analytics.fold_evaluations) >= 1
    assert analyze_result.analytics.stitched_oos_equity.point_count >= 1

    experiment_repo = RobustnessExperimentRepository(storage_root)
    persisted = experiment_repo.read_walk_forward_analytics(experiment_id)
    assert persisted.experiment_id == experiment_id
