"""Trades-to-bars aggregator tests."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.market.derivation import TradesToBarsAggregator
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.time.models.timeframe import Timeframe


def _synthetic_trades_across_minutes() -> list[MarketTrade]:
    specs = [
        (datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC), "100.00", 10, 0),
        (datetime(2025, 7, 13, 22, 0, 15, tzinfo=UTC), "101.50", 5, 1),
        (datetime(2025, 7, 13, 22, 0, 45, tzinfo=UTC), "99.25", 8, 2),
        (datetime(2025, 7, 13, 22, 0, 59, 500_000, tzinfo=UTC), "100.75", 3, 3),
        (datetime(2025, 7, 13, 22, 1, 0, tzinfo=UTC), "101.00", 12, 4),
    ]
    return [
        MarketTrade(
            price=Price(Decimal(price)),
            size=Volume(size),
            event_at=event_at,
            side=TradeSide.BUY if sequence % 2 == 0 else TradeSide.SELL,
            sequence=sequence,
        )
        for event_at, price, size, sequence in specs
    ]


def test_trades_to_bars_aggregator_builds_two_one_minute_bars() -> None:
    bars = TradesToBarsAggregator().aggregate(
        _synthetic_trades_across_minutes(),
        target_timeframe=Timeframe("1m"),
    )

    assert len(bars) == 2
    first = bars[0]
    assert first.open.value == Decimal("100.00")
    assert first.high.value == Decimal("101.50")
    assert first.low.value == Decimal("99.25")
    assert first.close.value == Decimal("100.75")
    assert first.volume.value == 26
    assert first.observed_at == datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC)
    assert first.available_at == datetime(2025, 7, 13, 22, 1, 0, tzinfo=UTC)


def test_trades_to_bars_aggregator_returns_empty_for_no_trades() -> None:
    bars = TradesToBarsAggregator().aggregate((), target_timeframe=Timeframe("1m"))
    assert bars == ()
