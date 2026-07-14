"""Tests for partitioned OHLCV batch reads."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet import ParquetDatasetRepository
from trading_framework.infrastructure.storage.parquet.writer import market_bars_to_table
from trading_framework.infrastructure.storage.paths import dataset_ohlcv_partition_path
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import HistoricalBarQuery
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="partitioned",
        ),
        version=1,
    )


def _bar(session_date: date, minute: int) -> MarketBar:
    observed_at = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        10,
        minute,
        tzinfo=UTC,
    )
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000 + minute),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_query_bars_reads_partitioned_dataset_in_time_order(tmp_path: Path) -> None:
    repository = ParquetDatasetRepository(tmp_path)
    dataset_ref = _dataset_ref()
    first_session = date(2024, 1, 2)
    second_session = date(2024, 1, 3)
    first_bars = [_bar(first_session, minute) for minute in range(3)]
    second_bars = [_bar(second_session, minute) for minute in range(2)]

    repository.write_session_table(
        dataset_ref,
        first_session,
        market_bars_to_table(first_bars),
    )
    repository.write_session_table(
        dataset_ref,
        second_session,
        market_bars_to_table(second_bars),
    )

    result = list(
        repository.query_bars(
            HistoricalBarQuery(
                dataset_ref=dataset_ref,
                start_at=datetime(2024, 1, 2, 10, 1, tzinfo=UTC),
                end_at=datetime(2024, 1, 3, 10, 0, tzinfo=UTC),
            )
        )
    )

    assert result == [_bar(first_session, 1), _bar(first_session, 2), _bar(second_session, 0)]
    assert dataset_ohlcv_partition_path(tmp_path, dataset_ref, first_session).exists()


def test_query_bars_batch_reads_many_partitions(tmp_path: Path) -> None:
    repository = ParquetDatasetRepository(tmp_path)
    dataset_ref = _dataset_ref()
    expected: list[MarketBar] = []
    for day in range(1, 6):
        session_date = date(2024, 1, day)
        bars = [_bar(session_date, minute) for minute in range(2)]
        expected.extend(bars)
        repository.write_session_table(dataset_ref, session_date, market_bars_to_table(bars))

    result = list(
        repository.query_bars(
            HistoricalBarQuery(
                dataset_ref=dataset_ref,
                start_at=datetime(2024, 1, 1, tzinfo=UTC),
                end_at=datetime(2024, 1, 31, tzinfo=UTC),
            )
        )
    )

    assert result == expected
    assert len(result) == 10
