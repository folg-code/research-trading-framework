"""Storage path helpers derived from dataset identity."""

from pathlib import Path

from trading_framework.market.datasets import DatasetRef


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
