"""Tests for research and robustness dashboard view helpers."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from dashboard_app.query import DashboardQueryService
from dashboard_app.views.research import list_research_runs, load_research_run
from dashboard_app.views.robustness import (
    build_verdict_checklist,
    list_robustness_experiments,
    load_robustness_experiment,
)


def test_load_research_run_tables(tmp_path: Path) -> None:
    run_dir = tmp_path / "research" / "market_research" / "runs" / "s1"
    analytics = run_dir / "analytics"
    analytics.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        """
        {
          "run_id": "s1",
          "schema_version": "signal_research.v2",
          "framework_version": "0.1",
          "created_at_utc": "2024-06-02T10:00:00+00:00",
          "source_dataset_ref": "NQ.c.0|ohlcv|1m|csv|x@1",
          "evaluation_timeframe": "1m",
          "research_scope": "signal_model_only",
          "signal_model_ids": ["sig"],
          "horizon_bars_requested": [5],
          "reference_price_policy": "close_at_detected_at",
          "outcome_definition_fingerprint": "fp"
        }
        """.strip(),
        encoding="utf-8",
    )
    pq.write_table(
        pa.table({"run_id": ["s1"], "horizon_bars": [5], "forward_return_mean": [0.01]}),
        analytics / "summary_metrics.parquet",
    )
    runs = list_research_runs(tmp_path)
    assert len(runs) == 1
    artifacts = load_research_run(DashboardQueryService(tmp_path), runs[0])
    assert "summary_metrics" in artifacts.tables
    assert artifacts.tables["summary_metrics"].num_rows == 1


def test_load_robustness_experiment_tables(tmp_path: Path) -> None:
    exp_dir = tmp_path / "research" / "strategy_robustness" / "experiments" / "rb1"
    analytics = exp_dir / "analytics"
    analytics.mkdir(parents=True)
    (exp_dir / "manifest.json").write_text(
        """
        {
          "experiment_id": "rb1",
          "schema_version": "robustness_experiment.v1",
          "framework_version": "0.1",
          "created_at_utc": "2024-06-05T10:00:00+00:00",
          "simulation_assumptions_fingerprint": "abc",
          "spec": {"dataset_ref": "NQ.c.0|ohlcv|1m|csv|x@1", "timeframe": "1m"}
        }
        """.strip(),
        encoding="utf-8",
    )
    pq.write_table(
        pa.table({"experiment_id": ["rb1"], "rank": [1], "config_id": ["c1"]}),
        analytics / "parameter_sweep_rankings.parquet",
    )
    (analytics / "verdict.json").write_text(
        '{"experiment_id":"rb1","passed":true}', encoding="utf-8"
    )
    experiments = list_robustness_experiments(tmp_path)
    assert len(experiments) == 1
    artifacts = load_robustness_experiment(DashboardQueryService(tmp_path), experiments[0])
    assert "parameter_sweep_rankings" in artifacts.tables
    assert artifacts.verdict is not None


def test_build_verdict_checklist_maps_gates_and_headline() -> None:
    checklist = build_verdict_checklist(
        {
            "verdict": "CONDITIONAL",
            "summary": "Soft gate failed.",
            "strengths": ["stable walk-forward"],
            "weaknesses": ["stress drop"],
            "blocking_issues": [],
            "gate_results": [
                {
                    "gate_id": "max_worst_stress_delta_net_pnl",
                    "passed": False,
                    "severity": "SOFT",
                    "message": "Stress delta too large",
                    "observed_value": "-25",
                },
                {
                    "gate_id": "min_stitched_oos_net_pnl",
                    "passed": True,
                    "severity": "HARD",
                    "message": "OOS profit ok",
                },
            ],
        }
    )

    assert checklist.verdict == "CONDITIONAL"
    assert "softer checks" in checklist.headline
    assert checklist.gates[0].label == "Worst stress-test drop"
    assert checklist.gates[0].passed is False
    assert checklist.gates[1].passed is True
    assert checklist.strengths == ("stable walk-forward",)
