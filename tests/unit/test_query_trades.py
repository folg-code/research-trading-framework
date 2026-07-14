"""Query trades use case tests."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data.query_trades import QueryTradesRequest, query_trades
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketTrade, TradeSide
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
        version=1,
    )


def _trade(second: int) -> MarketTrade:
    event_at = datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC)
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=event_at,
        side=TradeSide.BUY,
    )


def _published_metadata(dataset_ref: DatasetRef) -> DatasetMetadata:
    start_at = datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 13, 22, 0, 2, tzinfo=UTC)
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=Identifier("NQ.c.0"),
        timeframe=Timeframe("tick"),
        provider="databento",
        source_id="nq_cme_trades_2024",
        data_type="trades",
        start_at=start_at,
        end_at=end_at,
        schema_version="trades.v1",
        normalization_version="databento-trades-v1",
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=DatasetLifecycleState.PUBLISHED,
        row_count=3,
        checksum="abc123",
        created_at=start_at,
        published_at=datetime(2025, 7, 14, tzinfo=UTC),
    )


def test_query_trades_returns_published_trades_in_event_time_order(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetTradeDatasetRepository(storage_root)
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
    repository.write_trades(dataset_ref, [_trade(2), _trade(0), _trade(1)])

    trades = query_trades(
        QueryTradesRequest(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC),
            end_at=datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC),
        ),
        storage_root=storage_root,
        registry=registry,
        repository=repository,
    )

    assert [trade.event_at.second for trade in trades] == [0, 1]
    assert all(trade.event_at.tzinfo is not None for trade in trades)


def test_query_trades_rejects_non_published_dataset(tmp_path: Path) -> None:
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
        query_trades(
            QueryTradesRequest(
                dataset_ref=dataset_ref,
                start_at=datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC),
                end_at=datetime(2025, 7, 13, 22, 0, 2, tzinfo=UTC),
            ),
            storage_root=storage_root,
            registry=registry,
        )
