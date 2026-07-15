"""Integration-style tests for Monte Carlo and diagnostics orchestration."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_monte_carlo_diagnostics_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    AnalyzeDiagnosticsExperimentRequest,
    AnalyzeMonteCarloExperimentRequest,
    RunMonteCarloExperimentRequest,
    analyze_diagnostics_experiment,
    analyze_monte_carlo_experiment,
    run_monte_carlo_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_run_and_analyze_monte_carlo_and_diagnostics(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-monte-carlo-diagnostics"
    spec = build_monte_carlo_diagnostics_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )

    run_result = run_monte_carlo_experiment(
        RunMonteCarloExperimentRequest(
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

    assert run_result.results.reference_strategy_run_id
    assert len(run_result.results.methods) == 3

    mc_analyze_result = analyze_monte_carlo_experiment(
        AnalyzeMonteCarloExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
        )
    )
    assert len(mc_analyze_result.analytics.distribution_summaries) == 3
    assert len(mc_analyze_result.analytics.tail_probabilities) == 3

    diagnostics_result = analyze_diagnostics_experiment(
        AnalyzeDiagnosticsExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            link_walk_forward=False,
        )
    )
    assert diagnostics_result.analytics.pnl_concentration.top_k_trades == 2
    assert diagnostics_result.analytics.temporal_stability.bucket_count >= 0

    experiment_repo = RobustnessExperimentRepository(storage_root)
    persisted_mc = experiment_repo.read_monte_carlo_analytics(experiment_id)
    persisted_diag = experiment_repo.read_diagnostics_analytics(experiment_id)
    assert persisted_mc.experiment_id == experiment_id
    assert persisted_diag.experiment_id == experiment_id
