"""Dataset identity and versioning tests."""

import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import (
    DatasetId,
    DatasetRef,
    DatasetVersionPolicy,
    InMemoryDatasetVersionAllocator,
    MaterialChangeReason,
)
from trading_framework.time.models.timeframe import Timeframe


def _sample_dataset_id() -> DatasetId:
    return DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
    )


def test_dataset_ref_round_trip() -> None:
    dataset_ref = DatasetRef(_sample_dataset_id(), version=3)
    assert DatasetRef.parse(str(dataset_ref)) == dataset_ref


def test_version_allocator_increments_per_dataset_id() -> None:
    allocator = InMemoryDatasetVersionAllocator()
    dataset_id = _sample_dataset_id()
    assert allocator.allocate_next(dataset_id) == 1
    assert allocator.allocate_next(dataset_id) == 2
    assert allocator.latest_version(dataset_id) == 2


def test_unchanged_physical_rewrite_does_not_require_new_version() -> None:
    requires_new = DatasetVersionPolicy.requires_new_version(
        material_change=None,
        content_checksum_changed=False,
    )
    assert requires_new is False

    allocator = InMemoryDatasetVersionAllocator()
    dataset_id = _sample_dataset_id()
    first_version = allocator.allocate_next(dataset_id)
    reused = allocator.reuse_current(dataset_id)
    assert reused == first_version


def test_corrected_bar_requires_new_version() -> None:
    requires_new = DatasetVersionPolicy.requires_new_version(
        material_change=MaterialChangeReason.RECORDS_CORRECTED,
        content_checksum_changed=True,
    )
    assert requires_new is True

    allocator = InMemoryDatasetVersionAllocator()
    dataset_id = _sample_dataset_id()
    assert allocator.allocate_next(dataset_id) == 1
    assert allocator.allocate_next(dataset_id) == 2


def test_changed_normalization_requires_new_version() -> None:
    requires_new = DatasetVersionPolicy.requires_new_version(
        material_change=MaterialChangeReason.NORMALIZATION_CHANGED,
        content_checksum_changed=False,
    )
    assert requires_new is True


def test_dataset_ref_rejects_invalid_version() -> None:
    from trading_framework.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        DatasetRef(_sample_dataset_id(), version=0)
