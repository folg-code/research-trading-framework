"""Unit tests for compare_robustness_experiments."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_parameter_sweep_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    CompareRobustnessExperimentsRequest,
    RunRobustnessExperimentRequest,
    compare_robustness_experiments,
    run_robustness_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_compare_robustness_experiments_summarizes_completion_and_best_pnl(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-compare"
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

    result = compare_robustness_experiments(
        CompareRobustnessExperimentsRequest(
            experiment_ids=(experiment_id,),
            storage_root=storage_root,
        )
    )

    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.experiment_id == experiment_id
    assert row.total_configs == 2
    assert row.completed_configs == 2
    assert row.failed_configs == 0
    assert row.best_net_pnl is not None
    assert row.best_strategy_run_id is not None
