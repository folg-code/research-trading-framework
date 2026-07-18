"""Tests for cache fingerprint, datasource stubs, and query size limits."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dashboard_app.caching import cache_key_parts, compute_storage_fingerprint
from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, ChartWindow
from dashboard_app.datasources import (
    ParquetHistoricalRunDataSource,
    UnimplementedAwsDryRunDataSource,
)
from dashboard_app.query import DashboardQueryService, DatasetLocator


def test_storage_fingerprint_changes_when_child_appears(tmp_path: Path) -> None:
    research = tmp_path / "research"
    research.mkdir()
    first = compute_storage_fingerprint(tmp_path)
    (research / "market_research").mkdir()
    second = compute_storage_fingerprint(tmp_path)
    assert first.token != second.token
    parts = cache_key_parts(fingerprint=second, timeframe="1m", run_id="r1")
    assert second.token in parts


def test_aws_dry_run_datasource_stub_requires_status_url() -> None:
    source = UnimplementedAwsDryRunDataSource()
    with pytest.raises(NotImplementedError, match="DASHBOARD_STATUS_URL"):
        source.list_live_sessions()
    with pytest.raises(NotImplementedError, match="DASHBOARD_STATUS_URL"):
        source.fetch_session_snapshot("session-1")


def test_historical_datasource_lists_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / "st1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        """
        {
          "run_id": "st1",
          "schema_version": "strategy_research.v1",
          "framework_version": "0.1",
          "created_at_utc": "2024-06-04T10:00:00+00:00",
          "source_dataset_ref": "NQ.c.0|ohlcv|1m|csv|x@1",
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
    source = ParquetHistoricalRunDataSource(tmp_path)
    catalog = source.list_runs()
    assert len(catalog.runs) == 1
    assert catalog.runs[0].run_id == "st1"


def test_read_parquet_columns_applies_default_row_cap(tmp_path: Path) -> None:
    path = tmp_path / "rows.parquet"
    pq.write_table(pa.table({"value": list(range(10))}), path)
    service = DashboardQueryService(tmp_path, max_parquet_rows=3)
    table = service.read_parquet_columns(path)
    assert table.num_rows == 3


def test_historical_ohlcv_window_uses_query_service(tmp_path: Path) -> None:
    ref = "NQ.c.0|ohlcv|1m|csv|partitioned@1"
    locator = DatasetLocator.parse(ref)
    day = locator.ohlcv_partitions_dir(tmp_path) / "session_date=2024-01-02"
    day.mkdir(parents=True)
    observed = datetime(2024, 1, 2, 10, 0, tzinfo=UTC).replace(tzinfo=None)
    pq.write_table(
        pa.table(
            {
                "open": ["100"],
                "high": ["100"],
                "low": ["100"],
                "close": ["100"],
                "volume": [1],
                "observed_at": pa.array([observed], type=pa.timestamp("us")),
                "available_at": pa.array(
                    [observed + timedelta(minutes=1)], type=pa.timestamp("us")
                ),
            }
        ),
        day / "bars.parquet",
    )
    source = ParquetHistoricalRunDataSource(tmp_path)
    result = source.read_ohlcv_window(
        dataset_ref=ref,
        window=ChartWindow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            start_at_utc=datetime(2024, 1, 2, tzinfo=UTC),
            end_at_utc=datetime(2024, 1, 3, tzinfo=UTC),
            timeframe="1m",
        ),
    )
    assert len(result.bars) == 1
