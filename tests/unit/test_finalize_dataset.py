"""Finalize dataset use case tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data.finalize_dataset import finalize_dataset
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketBar
from trading_framework.time.models.timeframe import Timeframe


def _dataset_id() -> DatasetId:
    return DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
    )


def _bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _working_metadata(dataset_ref: DatasetRef) -> DatasetMetadata:
    start_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 12, 1, tzinfo=UTC)
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
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=2,
        checksum="pending",
        created_at=start_at,
    )


def test_finalize_dataset_transitions_working_to_finalized(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)
    dataset_ref = registry.allocate_ref(_dataset_id())
    registry.register(_working_metadata(dataset_ref))
    repository.write_bars(dataset_ref, [_bar(0), _bar(1)])

    result_ref = finalize_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        repository=repository,
    )
    metadata = registry.get(result_ref)

    assert metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert metadata.checksum != "pending"
    assert metadata.row_count == 2


def test_finalize_dataset_rejects_failed_validation(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = DatasetRef(dataset_id=_dataset_id(), version=1)
    registry.register(
        replace(
            _working_metadata(dataset_ref),
            validation_status=ValidationStatus.FAILED,
        )
    )

    with pytest.raises(ValidationError, match="validation must pass"):
        finalize_dataset(dataset_ref, storage_root=storage_root, registry=registry)


def test_finalize_dataset_is_idempotent_for_published(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = DatasetRef(dataset_id=_dataset_id(), version=1)
    registry.register(_working_metadata(dataset_ref))
    registry.update(
        replace(
            _working_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.PUBLISHED,
        )
    )

    result_ref = finalize_dataset(dataset_ref, storage_root=storage_root, registry=registry)

    assert result_ref == dataset_ref
    assert registry.get(result_ref).lifecycle_status is DatasetLifecycleState.PUBLISHED
