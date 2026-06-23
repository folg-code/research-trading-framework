"""Query historical use case tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
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


def _published_metadata(dataset_ref: DatasetRef) -> DatasetMetadata:
    start_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 12, 2, tzinfo=UTC)
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
        lifecycle_status=DatasetLifecycleState.PUBLISHED,
        row_count=3,
        checksum="abc123",
        created_at=start_at,
        published_at=datetime(2024, 6, 2, tzinfo=UTC),
    )


def test_query_historical_returns_published_bars_in_time_order(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _published_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
            published_at=None,
        )
    )
    registry.update(
        replace(
            _published_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.FINALIZED,
            published_at=None,
        )
    )
    registry.update(_published_metadata(dataset_ref))
    repository.write_bars(dataset_ref, [_bar(2), _bar(0), _bar(1)])

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=dataset_ref,
            start_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            end_at=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
        ),
        storage_root=storage_root,
        registry=registry,
        repository=repository,
    )

    assert [bar.observed_at.minute for bar in bars] == [0, 1]
    assert all(bar.observed_at.tzinfo is not None for bar in bars)


def test_query_historical_rejects_non_published_dataset(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _published_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
            published_at=None,
        )
    )

    with pytest.raises(ValidationError, match="published"):
        query_historical(
            QueryHistoricalRequest(
                dataset_ref=dataset_ref,
                start_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                end_at=datetime(2024, 1, 1, 12, 2, tzinfo=UTC),
            ),
            storage_root=storage_root,
            registry=registry,
        )
