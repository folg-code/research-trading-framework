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


def dataset_ohlcv_partitions_dir(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the session-date partition root for a partitioned OHLCV dataset version."""
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
        / "partitions"
    )


def dataset_ohlcv_partition_path(
    root: Path,
    dataset_ref: DatasetRef,
    session_date: date,
) -> Path:
    """Return the Parquet path for one session-date OHLCV partition."""
    partition_dir = (
        dataset_ohlcv_partitions_dir(root, dataset_ref) / f"session_date={session_date.isoformat()}"
    )
    return partition_dir / "bars.parquet"


def list_ohlcv_session_dates(root: Path, dataset_ref: DatasetRef) -> list[date]:
    """Return sorted session dates present for a partitioned OHLCV dataset version."""
    partitions_dir = dataset_ohlcv_partitions_dir(root, dataset_ref)
    if not partitions_dir.exists():
        return []
    session_dates: list[date] = []
    for partition_dir in partitions_dir.iterdir():
        if not partition_dir.is_dir() or not partition_dir.name.startswith("session_date="):
            continue
        session_dates.append(date.fromisoformat(partition_dir.name.split("=", 1)[1]))
    return sorted(session_dates)


def continuous_ohlcv_manifest_path(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the continuous OHLCV manifest path for one dataset version."""
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
        / "continuous_ohlcv_manifest.json"
    )


def signal_research_run_dir(root: Path, run_id: str) -> Path:
    """Return the run envelope directory for one Signal Research run."""
    return root / run_id


def strategy_research_run_dir(root: Path, run_id: str) -> Path:
    """Return the run envelope directory for one Strategy Research run."""
    return root / "strategy_research" / run_id


def robustness_experiment_dir(root: Path, experiment_id: str) -> Path:
    """Return the storage directory for one robustness experiment."""
    return root / "robustness_experiments" / experiment_id


def robustness_experiment_folds_dir(root: Path, experiment_id: str) -> Path:
    """Return the folds directory for one robustness experiment."""
    return robustness_experiment_dir(root, experiment_id) / "folds"


def robustness_experiment_analytics_dir(root: Path, experiment_id: str) -> Path:
    """Return the analytics directory for one robustness experiment."""
    return robustness_experiment_dir(root, experiment_id) / "analytics"


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


def dataset_contract_trades_partitions_dir(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the session-date partition root for a contract trade dataset version."""
    return dataset_trades_version_dir(root, dataset_ref) / "partitions"


def dataset_contract_trades_partition_path(
    root: Path,
    dataset_ref: DatasetRef,
    session_date: date,
) -> Path:
    """Return the Parquet path for one session-date partition."""
    partition_dir = (
        dataset_contract_trades_partitions_dir(root, dataset_ref)
        / f"session_date={session_date.isoformat()}"
    )
    return partition_dir / "trades.parquet"


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


def list_contract_session_dates(root: Path, dataset_ref: DatasetRef) -> list[date]:
    """Return sorted session dates present for a contract trade dataset version."""
    partitions_dir = dataset_contract_trades_partitions_dir(root, dataset_ref)
    if not partitions_dir.exists():
        return []
    session_dates: list[date] = []
    for partition_dir in partitions_dir.iterdir():
        if not partition_dir.is_dir() or not partition_dir.name.startswith("session_date="):
            continue
        session_dates.append(date.fromisoformat(partition_dir.name.split("=", 1)[1]))
    return sorted(session_dates)


def roll_schedule_version_dir(
    root: Path,
    *,
    product: str,
    policy_slug: str,
    version: int,
) -> Path:
    """Return the storage directory for one roll schedule version."""
    return root / "continuous" / "schedules" / product / policy_slug / f"v{version}"


def roll_schedule_parquet_path(
    root: Path,
    *,
    product: str,
    policy_slug: str,
    version: int,
) -> Path:
    """Return the Parquet path for one roll schedule version."""
    return (
        roll_schedule_version_dir(
            root,
            product=product,
            policy_slug=policy_slug,
            version=version,
        )
        / "schedule.parquet"
    )


def roll_schedule_manifest_path(
    root: Path,
    *,
    product: str,
    policy_slug: str,
    version: int,
) -> Path:
    """Return the manifest path for one roll schedule version."""
    return (
        roll_schedule_version_dir(
            root,
            product=product,
            policy_slug=policy_slug,
            version=version,
        )
        / "manifest.json"
    )


def continuous_trades_manifest_path(root: Path, dataset_ref: DatasetRef) -> Path:
    """Return the continuous trades manifest path for one dataset version."""
    return dataset_trades_version_dir(root, dataset_ref) / "continuous_manifest.json"


def list_continuous_session_dates(root: Path, dataset_ref: DatasetRef) -> list[date]:
    """Return sorted session dates present for a continuous trade dataset version."""
    return list_contract_session_dates(root, dataset_ref)
