"""Tests for columnar continuous trades to OHLCV aggregation."""

from datetime import UTC, date, datetime
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.continuous_trade_writer import (
    continuous_trade_records_to_table,
)
from trading_framework.infrastructure.storage.parquet.continuous_trades_to_ohlcv_table import (
    continuous_trades_table_to_ohlcv_table,
)
from trading_framework.infrastructure.storage.parquet.writer import market_bars_from_table
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.derivation import TradesToBarsAggregator
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.time.models.timeframe import Timeframe


def _trade(*, minute: int, second: int, price: str, size: int) -> ContinuousTradeRecord:
    event_at = datetime(2025, 7, 14, 14, minute, second, tzinfo=UTC)
    return ContinuousTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal(price)),
            size=Volume(size),
            event_at=event_at,
            side=TradeSide.BUY,
            received_at=event_at,
            trade_id=f"t-{minute}-{second}",
            sequence=second,
        ),
        actual_contract="NQU5",
        product="NQ",
        session_date=date(2025, 7, 14),
        continuous_symbol="NQ_CONT",
        roll_id="roll-1",
        is_roll_boundary=False,
    )


def test_continuous_trades_table_to_ohlcv_matches_domain_aggregator() -> None:
    records = [
        _trade(minute=0, second=0, price="100.25", size=2),
        _trade(minute=0, second=1, price="100.75", size=3),
        _trade(minute=1, second=0, price="101.00", size=1),
    ]
    trades_table = continuous_trade_records_to_table(records)

    polars_bars = market_bars_from_table(
        continuous_trades_table_to_ohlcv_table(trades_table, target_timeframe=Timeframe("1m"))
    )
    domain_bars = TradesToBarsAggregator().aggregate(
        [record.trade for record in records],
        target_timeframe=Timeframe("1m"),
    )

    assert len(polars_bars) == len(domain_bars)
    for polars_bar, domain_bar in zip(polars_bars, domain_bars, strict=True):
        assert polars_bar.open == domain_bar.open
        assert polars_bar.high == domain_bar.high
        assert polars_bar.low == domain_bar.low
        assert polars_bar.close == domain_bar.close
        assert polars_bar.volume == domain_bar.volume
        assert polars_bar.observed_at == domain_bar.observed_at
        assert polars_bar.available_at == domain_bar.available_at


def test_continuous_trades_table_to_ohlcv_skips_empty_input() -> None:
    table = continuous_trade_records_to_table([])

    result = continuous_trades_table_to_ohlcv_table(table)

    assert result.num_rows == 0
