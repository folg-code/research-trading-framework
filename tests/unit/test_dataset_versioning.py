"""Dataset versioning policy tests."""

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import (
    DatasetId,
    DatasetVersionPolicy,
    InMemoryDatasetVersionAllocator,
    MaterialChangeReason,
)
from trading_framework.time.models.timeframe import Timeframe


def _dataset_id() -> DatasetId:
    return DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
    )


def test_dataset_version_policy_requires_new_version_for_material_change() -> None:
    assert (
        DatasetVersionPolicy.requires_new_version(
            material_change=MaterialChangeReason.SOURCE_DATA_CHANGED,
            content_checksum_changed=False,
        )
        is True
    )


def test_dataset_version_policy_requires_new_version_for_checksum_change() -> None:
    assert (
        DatasetVersionPolicy.requires_new_version(
            material_change=None,
            content_checksum_changed=True,
        )
        is True
    )


def test_dataset_version_policy_reuses_version_for_physical_rewrite() -> None:
    assert (
        DatasetVersionPolicy.requires_new_version(
            material_change=None,
            content_checksum_changed=False,
        )
        is False
    )


def test_in_memory_dataset_version_allocator_allocates_monotonic_versions() -> None:
    allocator = InMemoryDatasetVersionAllocator()
    dataset_id = _dataset_id()

    assert allocator.allocate_next(dataset_id) == 1
    assert allocator.allocate_next(dataset_id) == 2
    assert allocator.latest_version(dataset_id) == 2
    assert allocator.reuse_current(dataset_id) == 2
