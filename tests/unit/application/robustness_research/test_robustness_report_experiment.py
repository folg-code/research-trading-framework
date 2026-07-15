"""Integration-style tests for full robustness analyze + HTML report."""

from __future__ import annotations

from pathlib import Path

from tests.unit.application.robustness_research.conftest import (
    build_monte_carlo_diagnostics_spec,
    write_published_dataset,
)
from trading_framework.application.robustness_research import (
    AnalyzeRobustnessExperimentRequest,
    RenderRobustnessReportRequest,
    RunMonteCarloExperimentRequest,
    analyze_robustness_experiment,
    render_robustness_experiment_report,
    run_monte_carlo_experiment,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.robustness.verdict import VerdictKind
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_analyze_and_render_robustness_dashboard(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    experiment_id = "exp-robustness-report"
    spec = build_monte_carlo_diagnostics_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
    )

    run_monte_carlo_experiment(
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

    analyze_result = analyze_robustness_experiment(
        AnalyzeRobustnessExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
        )
    )
    assert analyze_result.verdict.verdict in {
        VerdictKind.PASS,
        VerdictKind.CONDITIONAL,
        VerdictKind.FAIL,
    }

    report_path = tmp_path / "dashboard.html"
    render_result = render_robustness_experiment_report(
        RenderRobustnessReportRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            output_path=report_path,
            persist_to_experiment_dir=False,
        )
    )
    html = render_result.output_path.read_text(encoding="utf-8")
    assert analyze_result.verdict.verdict.value in html
    assert "verdict-hero" in html
    assert "Monte Carlo" in html

    repo = RobustnessExperimentRepository(storage_root)
    persisted_verdict = repo.read_verdict(experiment_id)
    assert persisted_verdict.experiment_id == experiment_id
