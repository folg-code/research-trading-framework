"""File dataset registry tests."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import dataset_metadata_path
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    ValidationStatus,
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


def _working_metadata(dataset_ref: object) -> DatasetMetadata:
    from trading_framework.market.datasets import DatasetRef

    assert isinstance(dataset_ref, DatasetRef)
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 1, 0, tzinfo=UTC)
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=Identifier("ES.c.0"),
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
        data_type="ohlcv",
        start_at=start_at,
        end_at=end_at,
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        validation_status=ValidationStatus.PENDING,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=0,
        checksum="pending",
        created_at=start_at,
    )


def test_file_dataset_registry_registers_and_retrieves_working_metadata(
    tmp_path: Path,
) -> None:
    registry = FileDatasetRegistry(tmp_path)
    dataset_ref = registry.allocate_ref(_dataset_id())
    metadata = _working_metadata(dataset_ref)

    registry.register(metadata)
    loaded = registry.get(dataset_ref)

    assert loaded == metadata
    assert dataset_metadata_path(tmp_path, dataset_ref).exists()


def test_file_dataset_registry_allocates_monotonic_versions(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    dataset_id = _dataset_id()

    first = registry.allocate_ref(dataset_id)
    second = registry.allocate_ref(dataset_id)

    assert first.version == 1
    assert second.version == 2


def test_file_dataset_registry_rejects_non_working_metadata(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    dataset_ref = registry.allocate_ref(_dataset_id())
    metadata = replace(
        _working_metadata(dataset_ref),
        lifecycle_status=DatasetLifecycleState.FINALIZED,
    )

    with pytest.raises(ValidationError, match="WORKING"):
        registry.register(metadata)


def test_file_dataset_registry_rejects_published_metadata_update(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    dataset_ref = registry.allocate_ref(_dataset_id())
    registry.register(_working_metadata(dataset_ref))
    published = replace(
        _working_metadata(dataset_ref),
        lifecycle_status=DatasetLifecycleState.PUBLISHED,
    )
    registry.update(
        replace(
            _working_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.FINALIZED,
        )
    )
    registry.update(published)

    with pytest.raises(ValidationError, match="immutable"):
        registry.update(
            replace(
                published,
                checksum="changed",
            )
        )


def test_file_dataset_registry_path_is_derived_from_identity(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    dataset_ref = registry.allocate_ref(_dataset_id())
    registry.register(_working_metadata(dataset_ref))

    expected = tmp_path / "metadata" / "ES.c.0" / "ohlcv" / "1m" / "csv" / "sample-file" / "v1.json"
    assert dataset_metadata_path(tmp_path, dataset_ref) == expected
