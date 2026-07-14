"""Aggregate canonical trades into OHLCV bars."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar, MarketTrade
from trading_framework.market.temporal import derive_bar_interval
from trading_framework.time.models.timeframe import Timeframe


def _bucket_start(event_at: datetime, timeframe: Timeframe) -> datetime:
    """Floor ``event_at`` to a UTC left-labeled bucket start."""
    if timeframe.is_event_level:
        msg = "event-level timeframe tick has no bar buckets"
        raise ValidationError(msg)
    seconds = timeframe.total_seconds
    aware = event_at.astimezone(UTC)
    epoch = int(aware.timestamp())
    floored = epoch - (epoch % seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


def _trade_sort_key(trade: MarketTrade) -> tuple[datetime, int]:
    sequence = trade.sequence if trade.sequence is not None else 0
    return trade.event_at, sequence


class TradesToBarsAggregator:
    """Aggregate canonical trades into left-labeled OHLCV bars."""

    def aggregate(
        self,
        trades: Sequence[MarketTrade],
        *,
        target_timeframe: Timeframe,
    ) -> tuple[MarketBar, ...]:
        """Return OHLCV bars for non-empty trade buckets; omit empty buckets."""
        if target_timeframe.is_event_level:
            msg = "target_timeframe must represent a bar duration"
            raise ValidationError(msg)
        if not trades:
            return ()

        sorted_trades = sorted(trades, key=_trade_sort_key)
        bars: list[MarketBar] = []
        current_bucket: datetime | None = None
        bucket_trades: list[MarketTrade] = []

        def flush() -> None:
            nonlocal bucket_trades, current_bucket
            if not bucket_trades or current_bucket is None:
                return
            prices = [trade.price.value for trade in bucket_trades]
            observed_at, available_at = derive_bar_interval(current_bucket, target_timeframe)
            bars.append(
                MarketBar(
                    open=Price(prices[0]),
                    high=Price(max(prices)),
                    low=Price(min(prices)),
                    close=Price(prices[-1]),
                    volume=Volume(sum(int(trade.size.value) for trade in bucket_trades)),
                    observed_at=observed_at,
                    available_at=available_at,
                )
            )
            bucket_trades = []

        for trade in sorted_trades:
            trade_bucket = _bucket_start(trade.event_at, target_timeframe)
            if current_bucket is None:
                current_bucket = trade_bucket
            if trade_bucket != current_bucket:
                flush()
                current_bucket = trade_bucket
            bucket_trades.append(trade)

        flush()
        return tuple(bars)
