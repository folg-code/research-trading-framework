"""Focused coverage for rich public Strategy Research evidence (Sprint 070)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from dashboard_app.publication.generator import RawArtifactInput, build_projection_bundle
from dashboard_app.publication.table_loading import bounded_row_indexes, load_table
from dashboard_app.publication.workspace import (
    STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS,
    discover_strategy_research_evidence_inputs,
)


def _write_strategy_run(
    storage_root: Path,
    *,
    run_id: str,
    equity_rows: int,
    experiment_id: str | None = None,
) -> None:
    run_dir = storage_root / "research" / "strategy_research" / "runs" / run_id
    analytics_dir = run_dir / "analytics"
    analytics_dir.mkdir(parents=True)

    manifest: dict[str, object] = {
        "run_id": run_id,
        "schema_version": "strategy_research.v1",
        "framework_version": "0.1.0",
        "created_at_utc": "2026-09-18T00:00:00+00:00",
        "source_dataset_ref": "TEST.INST|ohlcv|1m|csv|fixture@1",
        "evaluation_timeframe": "1m",
        "strategy_model_id": "test_strategy",
        "market_model_id": "test_market",
        "signal_model_id": "test_signal",
        "exit_model_id": "fixed_bars",
        "risk_model_id": "fixed_quantity",
        "fill_policy_entry": "next_bar_open",
        "fill_policy_exit": "next_bar_open",
        "slippage_bps": "0",
        "commission_per_side": "0",
        "initial_capital": "100000",
        "strategy_source_ref": "pkg.module:build_strategy",
    }
    if experiment_id is not None:
        manifest["experiment_id"] = experiment_id
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    pq.write_table(
        pa.table(
            {
                "observed_at": list(range(equity_rows)),
                "equity": [float(i) for i in range(equity_rows)],
                "drawdown": [0.0] * equity_rows,
                "open_position_count": [0] * equity_rows,
            }
        ),
        run_dir / "equity.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "net_pnl": [10.0, -5.0],
                "exit_reason": ["target", "stop"],
                "entry_fill_price": [100.0, 101.0],
                "quantity": [1.0, 1.0],
            }
        ),
        run_dir / "trades.parquet",
    )
    pq.write_table(
        pa.table({"run_id": [run_id], "net_pnl": [5.0], "trade_count": [2], "win_rate": [0.5]}),
        analytics_dir / "summary_metrics.parquet",
    )
    pq.write_table(
        pa.table({"episode_id": [0], "peak_equity": [100.0], "trough_equity": [90.0]}),
        analytics_dir / "drawdown_episodes.parquet",
    )
    pq.write_table(
        pa.table({"component_id": ["volatility.state"], "label": ["1.0"], "sample_count": [2]}),
        analytics_dir / "context_expectancy.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "observed_at": list(range(equity_rows)),
                "notional_exposure": [1.0] * equity_rows,
                "exposure_ratio": [0.01] * equity_rows,
            }
        ),
        analytics_dir / "exposure.parquet",
    )


def test_discovery_projects_every_field_and_table(tmp_path: Path) -> None:
    _write_strategy_run(tmp_path, run_id="run-1", equity_rows=3)

    inputs, skipped = discover_strategy_research_evidence_inputs(tmp_path)

    assert skipped == 0
    assert len(inputs) == 1
    item = inputs[0]
    assert item.artifact_role == "strategy_research_evidence"
    assert item.artifact_id == "strategy-research-evidence-run-1"
    assert item.raw_payload["strategy_source_ref"] == "pkg.module:build_strategy"
    tables = item.raw_payload["tables"]
    assert set(tables) == {
        "equity_curve",
        "trades",
        "summary_metrics",
        "drawdown_episodes",
        "context_expectancy",
        "exposure",
    }
    assert len(tables["trades"]) == 2


def test_discovery_excludes_robustness_experiment_child_runs(tmp_path: Path) -> None:
    """The 44 walk-forward child runs behind a robustness demo are not
    independent Strategy Research evidence -- ``list_runs`` already excludes
    any STRATEGY run whose manifest carries an ``experiment_id``, and this
    discovery function must not bypass that."""
    _write_strategy_run(
        tmp_path, run_id="child-run", equity_rows=2, experiment_id="demo-robustness-nq-half-year"
    )

    inputs, skipped = discover_strategy_research_evidence_inputs(tmp_path)

    assert inputs == []
    assert skipped == 0


def test_discovery_skips_run_missing_summary_metrics(tmp_path: Path) -> None:
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / "no-summary"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps({"run_id": "no-summary"}), encoding="utf-8")
    pq.write_table(pa.table({"observed_at": [0], "equity": [1.0]}), run_dir / "equity.parquet")

    inputs, skipped = discover_strategy_research_evidence_inputs(tmp_path)

    assert inputs == []
    assert skipped == 1


def test_discovery_bounds_dense_series(tmp_path: Path) -> None:
    _write_strategy_run(tmp_path, run_id="big-run", equity_rows=10_000)

    inputs, _ = discover_strategy_research_evidence_inputs(tmp_path)

    tables = inputs[0].raw_payload["tables"]
    assert len(tables["equity_curve"]) == STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS
    assert len(tables["exposure"]) == STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS
    # Trades are never bounded, however many there are.
    assert len(tables["trades"]) == 2


def test_sanitizer_drops_unknown_and_private_fields(tmp_path: Path) -> None:
    _write_strategy_run(tmp_path, run_id="run-1", equity_rows=3)
    inputs, _ = discover_strategy_research_evidence_inputs(tmp_path)
    item = inputs[0]
    payload = dict(item.raw_payload)
    payload["storage_path"] = "C:/private/run-1"
    tables = dict(payload["tables"])
    trades_rows = [dict(row) for row in tables["trades"]]
    trades_rows[0]["entry_fill_price"] = 100.0  # not allowlisted -- must be dropped
    tables["trades"] = trades_rows
    tables["unknown_table"] = [{"secret": "private"}]
    payload["tables"] = tables

    bundle = build_projection_bundle(
        [RawArtifactInput(item.artifact_id, item.artifact_role, payload)],
        generated_at_utc=datetime(2026, 9, 18, tzinfo=UTC),
    )
    projected = bundle.artifacts[item.artifact_id].fields

    assert "storage_path" not in projected
    assert "entry_fill_price" not in projected["tables"]["trades"][0]
    assert set(projected["tables"]["trades"][0]) == {"net_pnl", "exit_reason"}
    assert "unknown_table" not in projected["tables"]
    assert "private" not in repr(projected).lower()


def test_bounded_row_indexes_keeps_both_endpoints() -> None:
    indexes = bounded_row_indexes(10_000, 5)
    assert indexes[0] == 0
    assert indexes[-1] == 9_999
    assert len(indexes) == 5


def test_load_table_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_table(tmp_path / "absent.parquet") is None
