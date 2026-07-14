"""Shared helpers for the trades→bars spike (S012-T001)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.temporal import derive_bar_interval
from trading_framework.time.models.timeframe import Timeframe

DERIVATION_VERSION = "trades-to-bars-v1"


@dataclass(frozen=True, slots=True)
class AggregatedBarSample:
    """Prototype bar fields from one trades bucket."""

    observed_at: datetime
    available_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int


def bucket_start(event_at: datetime, timeframe: Timeframe) -> datetime:
    """Floor ``event_at`` to a UTC left-labeled bucket start."""
    if timeframe.value == "tick":
        msg = "tick timeframe has no bar buckets"
        raise ValueError(msg)
    seconds = timeframe.total_seconds
    if seconds <= 0:
        msg = "timeframe must represent a positive bar duration"
        raise ValueError(msg)
    aware = event_at.astimezone(UTC)
    epoch = int(aware.timestamp())
    floored = epoch - (epoch % seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


def _trade_sort_key(trade: MarketTrade) -> tuple[datetime, int]:
    sequence = trade.sequence if trade.sequence is not None else 0
    return trade.event_at, sequence


def aggregate_trades_to_bars(
    trades: Sequence[MarketTrade],
    *,
    target_timeframe: Timeframe,
) -> list[AggregatedBarSample]:
    """Aggregate trades into left-labeled OHLCV buckets (spike prototype)."""
    if not trades:
        return []

    sorted_trades = sorted(trades, key=_trade_sort_key)
    bars: list[AggregatedBarSample] = []
    current_bucket: datetime | None = None
    bucket_trades: list[MarketTrade] = []

    def flush() -> None:
        nonlocal bucket_trades, current_bucket
        if not bucket_trades or current_bucket is None:
            return
        prices = [trade.price.value for trade in bucket_trades]
        observed_at, available_at = derive_bar_interval(current_bucket, target_timeframe)
        bars.append(
            AggregatedBarSample(
                observed_at=observed_at,
                available_at=available_at,
                open=prices[0],
                high=max(prices),
                low=min(prices),
                close=prices[-1],
                volume=sum(int(trade.size.value) for trade in bucket_trades),
                trade_count=len(bucket_trades),
            )
        )
        bucket_trades = []

    for trade in sorted_trades:
        trade_bucket = bucket_start(trade.event_at, target_timeframe)
        if current_bucket is None:
            current_bucket = trade_bucket
        if trade_bucket != current_bucket:
            flush()
            current_bucket = trade_bucket
        bucket_trades.append(trade)

    flush()
    return bars


def synthetic_trades_across_minutes() -> list[MarketTrade]:
    """Build trades spanning two 1m buckets for spike validation."""
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


def iter_synthetic_bars() -> Iterator[AggregatedBarSample]:
    """Yield bars from the default synthetic trade fixture."""
    yield from aggregate_trades_to_bars(
        synthetic_trades_across_minutes(),
        target_timeframe=Timeframe("1m"),
    )


def validate_bucket_alignment(bar: AggregatedBarSample) -> bool:
    """Check observed_at + 1m == available_at for 1m bars."""
    return bar.available_at == bar.observed_at + timedelta(minutes=1)
