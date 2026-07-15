"""Map Binance USD-M futures payloads into framework contracts."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.execution.models import BestBidAskSnapshot
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    BinanceBookTickerPayload,
    BinanceKlinePayload,
)
from trading_framework.market.models import MarketBar


def _utc_from_millis(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def _volume_from_decimal_text(value: str) -> Volume:
    decimal_value = Decimal(value)
    if decimal_value < 0:
        msg = "volume must be non-negative"
        raise ValidationError(msg)
    integer_value = int(decimal_value.to_integral_value(rounding=ROUND_FLOOR))
    return Volume(integer_value)


def map_kline_payload(payload: BinanceKlinePayload) -> MarketBar:
    """Map a closed Binance 1m kline payload into a canonical MarketBar."""
    if payload.event_type != "kline":
        msg = "kline payload event_type must be 'kline'"
        raise ValidationError(msg)
    if payload.interval != "1m":
        msg = "only 1m Binance kline payloads are supported"
        raise ValidationError(msg)
    if not payload.is_closed:
        msg = "only closed Binance klines can be mapped to MarketBar"
        raise ValidationError(msg)
    observed_at = _utc_from_millis(payload.open_time_ms)
    # Binance kline close time is the final millisecond of the interval.
    available_at = _utc_from_millis(payload.close_time_ms) + timedelta(milliseconds=1)
    return MarketBar(
        open=Price(Decimal(payload.open_price)),
        high=Price(Decimal(payload.high_price)),
        low=Price(Decimal(payload.low_price)),
        close=Price(Decimal(payload.close_price)),
        volume=_volume_from_decimal_text(payload.volume),
        observed_at=observed_at,
        available_at=available_at,
    )


def map_book_ticker_payload(payload: BinanceBookTickerPayload) -> BestBidAskSnapshot:
    """Map a Binance bookTicker payload into a best bid/ask snapshot."""
    return BestBidAskSnapshot(
        symbol=payload.symbol,
        bid_price=Price(Decimal(payload.bid_price)),
        ask_price=Price(Decimal(payload.ask_price)),
        event_at=_utc_from_millis(payload.event_time_ms),
        received_at=_utc_from_millis(payload.transaction_time_ms),
    )
