"""Tests for catalog formatting and filters."""

from __future__ import annotations

from datetime import UTC, datetime

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, RunSummary, WorkflowKind
from dashboard_app.formatting import format_kpi, humanize_dataset_ref, instrument_from_dataset_ref
from dashboard_app.views.catalog_table import build_catalog_row, filter_catalog_runs


def _summary(**overrides: object) -> RunSummary:
    payload = {
        "schema_version": PRESENTATION_SCHEMA_VERSION,
        "workflow": WorkflowKind.STRATEGY,
        "run_id": "abc",
        "created_at_utc": datetime(2026, 7, 17, 20, 10, tzinfo=UTC),
        "title": "Strategy · high_vol_higher_low_fixed_exit · signal higher_low_long",
        "storage_path": "/tmp/run",
        "source_dataset_ref": "NQ.c.0|ohlcv|1m|csv|x@1",
        "evaluation_timeframe": "1m",
    }
    payload.update(overrides)
    return RunSummary(**payload)  # type: ignore[arg-type]


def test_humanize_dataset_ref_continuous_nq() -> None:
    assert instrument_from_dataset_ref("NQ.c.0|ohlcv|1m|csv|x@1") == "NQ"
    assert "NQ continuous" in humanize_dataset_ref("NQ.c.0|ohlcv|1m|csv|x@1")


def test_build_catalog_row_human_columns() -> None:
    row = build_catalog_row(_summary())
    assert row.instrument == "NQ"
    assert row.timeframe == "1m"
    assert "NQ continuous" in row.dataset
    assert "High Vol" in row.model or "High" in row.model
    assert "17 Jul 2026" in row.created


def test_filter_catalog_runs_by_workflow_and_instrument() -> None:
    runs = (
        _summary(run_id="s1"),
        _summary(
            run_id="m1",
            workflow=WorkflowKind.MARKET,
            title="Market · regime",
            source_dataset_ref="ES.c.0|ohlcv|1m|csv|x@1",
        ),
    )
    filtered = filter_catalog_runs(runs, workflow=WorkflowKind.STRATEGY, instrument="NQ")
    assert len(filtered) == 1
    assert filtered[0].run_id == "s1"


def test_format_kpi_units() -> None:
    assert format_kpi("net_pnl", 549.25) == "+549.25 pts"
    assert format_kpi("win_rate", 0.558) == "55.8%"
    assert format_kpi("total_return", 0.0055) == "+0.55%"
    assert format_kpi("trade_count", 208) == "208"
