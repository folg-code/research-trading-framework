"""Publish dataset use case tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data.publish_dataset import publish_dataset
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
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_PUBLISHED_AT = datetime(2024, 6, 2, 8, 0, tzinfo=UTC)


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
        ),
        version=1,
    )


def _bar() -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _finalized_metadata(dataset_ref: DatasetRef) -> DatasetMetadata:
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
        lifecycle_status=DatasetLifecycleState.FINALIZED,
        row_count=1,
        checksum="abc123",
        created_at=start_at,
    )


def test_publish_dataset_sets_published_at(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _finalized_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
        )
    )
    registry.update(_finalized_metadata(dataset_ref))

    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )
    metadata = registry.get(dataset_ref)

    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert metadata.published_at == _PUBLISHED_AT


def test_publish_dataset_blocks_repository_writes_for_published_version(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _finalized_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
        )
    )
    registry.update(_finalized_metadata(dataset_ref))
    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )

    repository = ParquetDatasetRepository(storage_root, metadata_reader=registry)
    with pytest.raises(ValidationError, match="immutable"):
        repository.write_bars(dataset_ref, [_bar()])


def test_publish_dataset_is_idempotent_when_already_published(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _finalized_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
        )
    )
    registry.update(
        replace(
            _finalized_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.PUBLISHED,
            published_at=_PUBLISHED_AT,
        )
    )

    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(datetime(2024, 6, 3, 8, 0, tzinfo=UTC)),
    )
    metadata = registry.get(dataset_ref)

    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert metadata.published_at == _PUBLISHED_AT
