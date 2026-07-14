"""Parquet trade repository tests."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.repositories import HistoricalTradeQuery
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


def _trade(*, day: int, second: int) -> MarketTrade:
    event_at = datetime(2025, 7, day, 22, 0, second, tzinfo=UTC)
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=event_at,
        side=TradeSide.BUY,
    )


def test_parquet_trade_repository_writes_day_partitions(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()

    repository.write_trades(dataset_ref, [_trade(day=13, second=0), _trade(day=14, second=1)])

    day_13 = (
        storage_root
        / "normalized/NQ.c.0/trades/tick/databento/nq_cme_trades_2024/v1/partitions"
        / "day=2025-07-13/trades.parquet"
    )
    day_14 = (
        storage_root
        / "normalized/NQ.c.0/trades/tick/databento/nq_cme_trades_2024/v1/partitions"
        / "day=2025-07-14/trades.parquet"
    )
    assert day_13.exists()
    assert day_14.exists()


def test_parquet_trade_repository_appends_within_same_day(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()

    repository.write_trades(dataset_ref, [_trade(day=13, second=0)])
    repository.write_trades(dataset_ref, [_trade(day=13, second=1)])

    trades = repository.query_trades(
        HistoricalTradeQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 0, 0, tzinfo=UTC),
            end_at=datetime(2025, 7, 13, 23, 59, 59, tzinfo=UTC),
        )
    )
    assert [trade.event_at.second for trade in trades] == [0, 1]


def test_parquet_trade_repository_queries_across_days_in_event_time_order(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()

    repository.write_trades(
        dataset_ref,
        [_trade(day=14, second=1), _trade(day=13, second=59), _trade(day=14, second=0)],
    )

    trades = repository.query_trades(
        HistoricalTradeQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC),
            end_at=datetime(2025, 7, 14, 22, 0, 1, tzinfo=UTC),
        )
    )

    assert [trade.event_at for trade in trades] == sorted(trade.event_at for trade in trades)
    assert len(trades) == 3


def test_parquet_trade_repository_prunes_partitions_by_time_range(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    repository.write_trades(dataset_ref, [_trade(day=13, second=0), _trade(day=14, second=0)])

    trades = repository.query_trades(
        HistoricalTradeQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC),
            end_at=datetime(2025, 7, 13, 23, 59, 59, tzinfo=UTC),
        )
    )

    assert len(trades) == 0
