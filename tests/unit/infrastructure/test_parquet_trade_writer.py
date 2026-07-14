"""Parquet trade writer tests."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.trade_writer import (
    MARKET_TRADE_PARQUET_SCHEMA,
    ParquetTradeWriter,
)
from trading_framework.market.models import MarketTrade, TradeSide


def _trade(
    *,
    second: int = 0,
    side: TradeSide = TradeSide.BUY,
    received_at: datetime | None = None,
    trade_id: str | None = "t-1",
    sequence: int | None = 42,
) -> MarketTrade:
    event_at = datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC)
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=event_at,
        side=side,
        received_at=received_at,
        trade_id=trade_id,
        sequence=sequence,
    )


def test_parquet_trade_writer_round_trips_trades(tmp_path: Path) -> None:
    path = tmp_path / "trades.parquet"
    trades = [_trade(second=0), _trade(second=1, side=TradeSide.SELL)]
    writer = ParquetTradeWriter()

    writer.write(path, trades)
    loaded = writer.read(path)

    assert loaded == trades


def test_parquet_trade_writer_round_trips_nullable_fields(tmp_path: Path) -> None:
    path = tmp_path / "trades.parquet"
    trade = _trade(received_at=None, trade_id=None, sequence=None)
    writer = ParquetTradeWriter()

    writer.write(path, [trade])
    loaded = writer.read(path)

    assert loaded == [trade]


def test_parquet_trade_writer_uses_stable_schema(tmp_path: Path) -> None:
    path = tmp_path / "trades.parquet"
    ParquetTradeWriter().write(path, [_trade()])

    schema = pq.read_schema(path)  # type: ignore[no-untyped-call]
    assert schema.equals(MARKET_TRADE_PARQUET_SCHEMA)
