"""Tests for strategy page helpers and overlay registry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dashboard_app.charts import DEFAULT_OVERLAY_REGISTRY, OverlayKind
from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, TradeView
from dashboard_app.query import DashboardQueryService
from dashboard_app.views.strategy import (
    chart_window_for_trade,
    list_strategy_runs,
    load_strategy_run,
    trades_to_views,
)


def test_overlay_registry_marks_orderflow_unimplemented() -> None:
    registration = DEFAULT_OVERLAY_REGISTRY.get(OverlayKind.ORDERFLOW_HISTOGRAM)
    assert registration.implemented is False
    assert OverlayKind.MARKERS in DEFAULT_OVERLAY_REGISTRY.implemented_kinds()
    assert OverlayKind.TRADE_CONNECTION in DEFAULT_OVERLAY_REGISTRY.implemented_kinds()


def test_chart_window_for_trade_pads_entry_exit() -> None:
    trade = TradeView(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        trade_id="t1",
        side="long",
        entry_at_utc=datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
        exit_at_utc=datetime(2024, 1, 2, 13, 0, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
    )
    window = chart_window_for_trade(trade, timeframe="1m", pad=timedelta(hours=1))
    assert window.start_at_utc == datetime(2024, 1, 2, 11, 0, tzinfo=UTC)
    assert window.end_at_utc == datetime(2024, 1, 2, 14, 0, tzinfo=UTC)


def test_trades_to_views_and_load_strategy_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / "st1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        """
        {
          "run_id": "st1",
          "schema_version": "strategy_research.v1",
          "framework_version": "0.1",
          "created_at_utc": "2024-06-04T10:00:00+00:00",
          "source_dataset_ref": "NQ.c.0|ohlcv|1m|csv|partitioned@1",
          "evaluation_timeframe": "1m",
          "strategy_model_id": "demo",
          "market_model_id": "m",
          "signal_model_id": "s",
          "exit_model_id": "e",
          "risk_model_id": "r",
          "simulation_assumptions_fingerprint": "abc"
        }
        """.strip(),
        encoding="utf-8",
    )
    trades = pa.table(
        {
            "trade_id": ["t1"],
            "direction": ["long"],
            "entry_fill_at": [datetime(2024, 1, 2, 12, 0, tzinfo=UTC)],
            "exit_fill_at": [datetime(2024, 1, 2, 13, 0, tzinfo=UTC)],
            "entry_fill_price": ["100.5"],
            "exit_fill_price": ["101.0"],
            "quantity": ["1"],
            "net_pnl": ["0.5"],
            "bars_held": [2],
        }
    )
    equity = pa.table(
        {
            "observed_at": [datetime(2024, 1, 2, 12, 0, tzinfo=UTC)],
            "equity": [100000.0],
            "drawdown": [0.0],
        }
    )
    metrics = pa.table(
        {
            "schema_version": ["strategy_research_analytics.v1"],
            "run_id": ["st1"],
            "net_pnl": ["0.5"],
            "trade_count": [1],
        }
    )
    pq.write_table(trades, run_dir / "trades.parquet")
    pq.write_table(equity, run_dir / "equity.parquet")
    (run_dir / "analytics").mkdir()
    pq.write_table(metrics, run_dir / "analytics" / "summary_metrics.parquet")

    runs = list_strategy_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0].run_id == "st1"

    service = DashboardQueryService(tmp_path)
    artifacts = load_strategy_run(service, runs[0])
    assert artifacts.metrics is not None
    assert artifacts.metrics["trade_count"] == 1
    views = trades_to_views(artifacts.trades)
    assert len(views) == 1
    assert views[0].trade_id == "t1"
    assert views[0].entry_price == pytest.approx(100.5)
