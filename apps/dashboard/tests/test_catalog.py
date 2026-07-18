"""Tests for presentation contracts and the run catalog."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dashboard_app.catalog import list_runs, load_run_manifest
from dashboard_app.contracts import (
    PRESENTATION_SCHEMA_VERSION,
    ChartWindow,
    TradeView,
    WorkflowKind,
)


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_presentation_contract_schema_version() -> None:
    window = ChartWindow(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        start_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        end_at_utc=datetime(2024, 1, 2, tzinfo=UTC),
        timeframe="5m",
        instrument_id="NQ",
        max_bars=500,
    )
    trade = TradeView(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        trade_id="t1",
        side="long",
        entry_at_utc=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        exit_at_utc=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        pnl=1.0,
    )
    assert window.schema_version == PRESENTATION_SCHEMA_VERSION
    assert trade.side == "long"


def test_list_runs_four_workflows_and_tolerates_corrupt(tmp_path: Path) -> None:
    root = tmp_path
    market_dir = root / "research" / "market_research" / "runs"
    strategy_dir = root / "research" / "strategy_research" / "runs"
    robustness_dir = root / "research" / "strategy_robustness" / "experiments"

    _write_manifest(
        market_dir / "m1" / "manifest.json",
        {
            "run_id": "m1",
            "schema_version": "signal_research.v2",
            "framework_version": "0.1",
            "created_at_utc": "2024-06-01T10:00:00+00:00",
            "source_dataset_ref": "NQ@continuous",
            "evaluation_timeframe": "5m",
            "research_scope": "market_model_only",
            "market_model_ids": ["regime_v1"],
            "signal_model_ids": [],
        },
    )
    _write_manifest(
        market_dir / "s1" / "manifest.json",
        {
            "run_id": "s1",
            "schema_version": "signal_research.v2",
            "framework_version": "0.1",
            "created_at_utc": "2024-06-02T10:00:00+00:00",
            "source_dataset_ref": "NQ@continuous",
            "evaluation_timeframe": "5m",
            "research_scope": "signal_model_only",
            "signal_model_ids": ["breakout_v1"],
        },
    )
    _write_manifest(
        market_dir / "both" / "manifest.json",
        {
            "run_id": "both",
            "schema_version": "signal_research.v2",
            "framework_version": "0.1",
            "created_at_utc": "2024-06-03T10:00:00+00:00",
            "source_dataset_ref": "NQ@continuous",
            "evaluation_timeframe": "5m",
            "research_scope": "market_and_signal",
            "signal_model_ids": ["breakout_v1"],
            "market_model_ids": ["regime_v1"],
        },
    )
    _write_manifest(
        strategy_dir / "st1" / "manifest.json",
        {
            "run_id": "st1",
            "schema_version": "strategy_research.v1",
            "framework_version": "0.1",
            "created_at_utc": "2024-06-04T10:00:00+00:00",
            "source_dataset_ref": "NQ@continuous",
            "evaluation_timeframe": "5m",
            "strategy_model_id": "demo_strategy",
            "market_model_id": "m",
            "signal_model_id": "s",
            "exit_model_id": "e",
            "risk_model_id": "r",
            "simulation_assumptions_fingerprint": "abc",
        },
    )
    _write_manifest(
        robustness_dir / "rb1" / "manifest.json",
        {
            "experiment_id": "rb1",
            "schema_version": "robustness_experiment.v1",
            "framework_version": "0.1",
            "created_at_utc": "2024-06-05T10:00:00+00:00",
            "simulation_assumptions_fingerprint": "abc",
            "spec": {
                "dataset_ref": "NQ@continuous",
                "timeframe": "5m",
                "strategy_template_id": "ema_cross_v1",
                "kinds": ["walk_forward", "parameter_sweep"],
            },
        },
    )
    # corrupt + missing required field
    (market_dir / "bad_json").mkdir(parents=True)
    (market_dir / "bad_json" / "manifest.json").write_text("{not-json", encoding="utf-8")
    _write_manifest(market_dir / "incomplete" / "manifest.json", {"schema_version": "x"})
    (market_dir / "no_manifest").mkdir(parents=True)

    catalog = list_runs(root)

    by_id = {item.run_id: item for item in catalog.runs}
    assert set(by_id) == {"m1", "s1", "both", "st1", "rb1"}
    assert by_id["m1"].workflow is WorkflowKind.MARKET
    assert by_id["s1"].workflow is WorkflowKind.SIGNAL
    assert by_id["both"].workflow is WorkflowKind.SIGNAL
    assert by_id["both"].research_scope == "market_and_signal"
    assert by_id["st1"].workflow is WorkflowKind.STRATEGY
    assert by_id["st1"].title == "Strategy · demo_strategy · signal s"
    assert by_id["rb1"].workflow is WorkflowKind.ROBUSTNESS
    assert by_id["rb1"].title == "Robustness · ema_cross_v1 · walk_forward, parameter_sweep"
    assert "rb1" not in by_id["rb1"].title
    assert catalog.runs[0].run_id == "rb1"
    assert len(catalog.issues) >= 3

    manifest = load_run_manifest(root, "st1")
    assert manifest is not None
    assert manifest.summary.run_id == "st1"
    assert manifest.identity["strategy_model_id"] == "demo_strategy"


def test_list_runs_empty_storage(tmp_path: Path) -> None:
    catalog = list_runs(tmp_path)
    assert catalog.runs == ()
    assert catalog.issues == ()
