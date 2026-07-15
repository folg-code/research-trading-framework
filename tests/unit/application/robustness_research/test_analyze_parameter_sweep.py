"""Integration-style tests for analyze_parameter_sweep orchestration."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_parameter_sweep_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    AnalyzeParameterSweepRequest,
    RunRobustnessExperimentRequest,
    analyze_parameter_sweep,
    run_robustness_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_analyze_parameter_sweep_persists_rankings_and_heatmaps(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-analyze-sweep"
    spec = build_parameter_sweep_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )
    run_robustness_experiment(
        RunRobustnessExperimentRequest(
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

    result = analyze_parameter_sweep(
        AnalyzeParameterSweepRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
        )
    )

    assert len(result.analytics.rankings) == 2
    assert result.analytics.rankings[0].rank == 1
    assert len(result.analytics.heatmaps) == 1
    assert len(result.analytics.neighbor_stability) == 2

    experiment_repo = RobustnessExperimentRepository(storage_root)
    persisted = experiment_repo.read_parameter_sweep_analytics(experiment_id)
    assert persisted.experiment_id == experiment_id
    assert len(persisted.rankings) == 2
