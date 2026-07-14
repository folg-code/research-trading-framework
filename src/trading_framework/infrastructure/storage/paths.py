"""Storage path helpers derived from dataset identity."""

from datetime import date, datetime, timedelta
from pathlib import Path

from trading_framework.market.datasets import DatasetRef
from trading_framework.time.models.utc_instant import require_utc_aware


def dataset_metadata_path(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the metadata file path for a dataset version."""
    dataset_id = dataset_ref.dataset_id
    return (
        root
        / "metadata"
        / dataset_id.instrument_id.value
        / dataset_id.data_type
        / dataset_id.timeframe.value
        / dataset_id.provider
        / dataset_id.source_id
        / f"v{dataset_ref.version}.json"
    )


def dataset_bars_path(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the Parquet bars path for a dataset version."""
    dataset_id = dataset_ref.dataset_id
    return (
        root
        / "normalized"
        / dataset_id.instrument_id.value
        / dataset_id.data_type
        / dataset_id.timeframe.value
        / dataset_id.provider
        / dataset_id.source_id
        / f"v{dataset_ref.version}"
        / "bars.parquet"
    )


def signal_research_run_dir(root: Path, run_id: str) -> Path:
    """Return the run envelope directory for one Signal Research run."""
    return root / run_id


def trade_event_partition_day(event_at: datetime) -> date:
    """Return the UTC calendar day used for trade dataset partitioning."""
    return require_utc_aware(event_at).date()


def partition_days_in_range(start_at: datetime, end_at: datetime) -> list[date]:
    """Return UTC calendar days overlapping a closed time range."""
    start_day = require_utc_aware(start_at).date()
    end_day = require_utc_aware(end_at).date()
    if end_day < start_day:
        return []
    days: list[date] = []
    current = start_day
    while current <= end_day:
        days.append(current)
        current += timedelta(days=1)
    return days


def dataset_trades_version_dir(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the version directory for a trade dataset."""
    dataset_id = dataset_ref.dataset_id
    return (
        root
        / "normalized"
        / dataset_id.instrument_id.value
        / dataset_id.data_type
        / dataset_id.timeframe.value
        / dataset_id.provider
        / dataset_id.source_id
        / f"v{dataset_ref.version}"
    )


def dataset_trades_partitions_dir(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the day-partition root for a trade dataset version."""
    return dataset_trades_version_dir(root, dataset_ref) / "partitions"


def dataset_trades_partition_path(root: Path, dataset_ref: DatasetRef, day: date) -> Path:
    """Return the Parquet path for one UTC day partition."""
    partition_dir = dataset_trades_partitions_dir(root, dataset_ref) / f"day={day.isoformat()}"
    return partition_dir / "trades.parquet"


def dataset_import_manifest_path(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the import manifest path for a trade dataset version."""
    return dataset_trades_version_dir(root, dataset_ref) / "import_manifest.json"
