"""Parquet dataset repository tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet import ParquetDatasetRepository
from trading_framework.infrastructure.storage.paths import dataset_bars_path
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository, HistoricalBarQuery
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


def test_parquet_dataset_repository_writes_and_queries_bars(tmp_path: Path) -> None:
    repository = ParquetDatasetRepository(tmp_path)
    dataset_ref = _dataset_ref()
    bars = [_bar(0), _bar(1), _bar(2)]

    repository.write_bars(dataset_ref, bars)
    result = repository.query_bars(
        HistoricalBarQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            end_at=datetime(2024, 1, 1, 12, 2, tzinfo=UTC),
        )
    )

    assert result == [_bar(1), _bar(2)]
    assert dataset_bars_path(tmp_path, dataset_ref).exists()


def test_parquet_dataset_repository_satisfies_protocol(tmp_path: Path) -> None:
    repository: DatasetRepository = ParquetDatasetRepository(tmp_path)
    dataset_ref = _dataset_ref()
    repository.write_bars(dataset_ref, [_bar(0)])
    assert (
        len(
            repository.query_bars(
                HistoricalBarQuery(
                    dataset_ref=dataset_ref,
                    start_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                    end_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                )
            )
        )
        == 1
    )
