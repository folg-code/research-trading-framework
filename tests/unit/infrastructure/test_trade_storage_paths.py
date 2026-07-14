"""Trade storage path helper tests."""

from datetime import UTC, date, datetime
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.paths import (
    dataset_import_manifest_path,
    dataset_trades_partition_path,
    dataset_trades_partitions_dir,
    dataset_trades_version_dir,
    partition_days_in_range,
    trade_event_partition_day,
)
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq_cme_trades_2024",
        ),
        version=2,
    )


def test_trade_event_partition_day_uses_utc_calendar_day() -> None:
    event_at = datetime(2025, 7, 13, 23, 30, tzinfo=UTC)
    assert trade_event_partition_day(event_at) == date(2025, 7, 13)


def test_partition_days_in_range_includes_boundary_days() -> None:
    start_at = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 14, 1, 0, tzinfo=UTC)
    assert partition_days_in_range(start_at, end_at) == [date(2025, 7, 13), date(2025, 7, 14)]


def test_trade_dataset_paths_follow_day_partition_layout(tmp_path: Path) -> None:
    root = tmp_path / "data"
    dataset_ref = _dataset_ref()
    day = date(2025, 7, 13)

    version_dir = dataset_trades_version_dir(root, dataset_ref)
    assert version_dir == (
        root
        / "normalized"
        / "NQ.c.0"
        / "trades"
        / "tick"
        / "databento"
        / "nq_cme_trades_2024"
        / "v2"
    )

    partitions_dir = dataset_trades_partitions_dir(root, dataset_ref)
    assert partitions_dir == version_dir / "partitions"

    partition_path = dataset_trades_partition_path(root, dataset_ref, day)
    assert partition_path == partitions_dir / "day=2025-07-13/trades.parquet"

    manifest_path = dataset_import_manifest_path(root, dataset_ref)
    assert manifest_path == version_dir / "import_manifest.json"
