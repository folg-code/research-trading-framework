"""Tests for dataset locator and DuckDB query service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, ChartWindow
from dashboard_app.dataset_locator import DatasetLocator
from dashboard_app.query import DashboardQueryService


def _dataset_ref() -> str:
    return "NQ.c.0|ohlcv|1m|csv|partitioned@1"


def _write_bars(path: Path, bars: list[tuple[datetime, str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    observed = [item[0].replace(tzinfo=None) for item in bars]
    table = pa.table(
        {
            "open": [item[1] for item in bars],
            "high": [item[1] for item in bars],
            "low": [item[1] for item in bars],
            "close": [item[1] for item in bars],
            "volume": [item[2] for item in bars],
            "observed_at": pa.array(observed, type=pa.timestamp("us")),
            "available_at": pa.array(
                [item + timedelta(minutes=1) for item in observed],
                type=pa.timestamp("us"),
            ),
        }
    )
    pq.write_table(table, path)


def test_dataset_locator_parse_and_path(tmp_path: Path) -> None:
    locator = DatasetLocator.parse(_dataset_ref())
    assert locator.instrument_id == "NQ.c.0"
    assert locator.version == 1
    partitions = locator.ohlcv_partitions_dir(tmp_path)
    assert partitions.name == "partitions"
    assert "NQ.c.0" in partitions.parts
    assert "v1" in partitions.parts


def test_dataset_locator_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="invalid dataset reference"):
        DatasetLocator.parse("not-a-ref")


def test_read_ohlcv_window_filters_and_orders(tmp_path: Path) -> None:
    locator = DatasetLocator.parse(_dataset_ref())
    day1 = locator.ohlcv_partitions_dir(tmp_path) / "session_date=2024-01-02"
    day2 = locator.ohlcv_partitions_dir(tmp_path) / "session_date=2024-01-03"
    _write_bars(
        day1 / "bars.parquet",
        [
            (datetime(2024, 1, 2, 10, 0, tzinfo=UTC), "100", 1),
            (datetime(2024, 1, 2, 10, 1, tzinfo=UTC), "101", 2),
            (datetime(2024, 1, 2, 10, 2, tzinfo=UTC), "102", 3),
        ],
    )
    _write_bars(
        day2 / "bars.parquet",
        [
            (datetime(2024, 1, 3, 10, 0, tzinfo=UTC), "103", 4),
            (datetime(2024, 1, 3, 10, 1, tzinfo=UTC), "104", 5),
        ],
    )

    service = DashboardQueryService(tmp_path)
    result = service.read_ohlcv_window(
        dataset_ref=_dataset_ref(),
        window=ChartWindow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            start_at_utc=datetime(2024, 1, 2, 10, 1, tzinfo=UTC),
            end_at_utc=datetime(2024, 1, 3, 10, 0, tzinfo=UTC),
            timeframe="1m",
        ),
    )

    assert [bar.close for bar in result.bars] == [101.0, 102.0, 103.0]
    assert result.truncated is False
    assert result.bars[0].observed_at_utc == datetime(2024, 1, 2, 10, 1, tzinfo=UTC)


def test_read_ohlcv_window_respects_max_bars(tmp_path: Path) -> None:
    locator = DatasetLocator.parse(_dataset_ref())
    day = locator.ohlcv_partitions_dir(tmp_path) / "session_date=2024-01-02"
    _write_bars(
        day / "bars.parquet",
        [
            (datetime(2024, 1, 2, 10, minute, tzinfo=UTC), str(100 + minute), minute)
            for minute in range(5)
        ],
    )
    service = DashboardQueryService(tmp_path)
    result = service.read_ohlcv_window(
        dataset_ref=_dataset_ref(),
        window=ChartWindow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            start_at_utc=datetime(2024, 1, 2, tzinfo=UTC),
            end_at_utc=datetime(2024, 1, 3, tzinfo=UTC),
            timeframe="1m",
            max_bars=2,
        ),
    )
    assert len(result.bars) == 2
    assert result.truncated is True
    assert [bar.volume for bar in result.bars] == [0, 1]


def test_read_ohlcv_missing_partitions_returns_empty(tmp_path: Path) -> None:
    service = DashboardQueryService(tmp_path)
    result = service.read_ohlcv_window(
        dataset_ref=_dataset_ref(),
        window=ChartWindow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            start_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            end_at_utc=datetime(2024, 1, 2, tzinfo=UTC),
            timeframe="1m",
        ),
    )
    assert result.bars == ()
    assert result.truncated is False


def test_read_parquet_columns_projection_and_strategy_helpers(tmp_path: Path) -> None:
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / "st1"
    run_dir.mkdir(parents=True)
    trades = pa.table(
        {
            "trade_id": ["a", "b"],
            "side": ["long", "short"],
            "pnl": [1.0, -2.0],
            "extra": ["x", "y"],
        }
    )
    equity = pa.table({"ts": [1, 2], "equity": [100.0, 101.0]})
    pq.write_table(trades, run_dir / "trades.parquet")
    pq.write_table(equity, run_dir / "equity.parquet")

    service = DashboardQueryService(tmp_path)
    projected = service.read_parquet_columns(
        run_dir / "trades.parquet",
        columns=["trade_id", "pnl"],
        limit=1,
    )
    assert projected.column_names == ["trade_id", "pnl"]
    assert projected.num_rows == 1
    assert service.read_strategy_trades(run_dir).num_rows == 2
    assert service.read_strategy_equity(run_dir).num_rows == 2
    missing = service.read_strategy_trades(run_dir / "missing")
    assert missing.num_rows == 0
