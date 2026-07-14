"""Storage encoding helpers for contract trade records."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketTrade, TradeSide

PRICE_NANOS_SCALE = 1_000_000_000
MISSING_TS_RECV_NS = 0


def utc_datetime_from_ns(ts_ns: int) -> datetime:
    """Decode UTC nanoseconds to an aware datetime."""
    seconds, remainder = divmod(ts_ns, 1_000_000_000)
    return datetime.fromtimestamp(seconds, tz=UTC).replace(microsecond=remainder // 1000)


def utc_ns_from_datetime(value: datetime) -> int:
    """Encode one UTC-aware datetime as nanoseconds since epoch."""
    timestamp = value.timestamp()
    seconds = int(timestamp)
    nanos = round((timestamp - seconds) * 1_000_000_000)
    return seconds * 1_000_000_000 + nanos


def price_nanos_from_decimal(value: Decimal) -> int:
    """Encode a decimal price as fixed-point nanos without float conversion."""
    scaled = value * PRICE_NANOS_SCALE
    return int(scaled.to_integral_value())


def decimal_price_from_nanos(price_nanos: int) -> Decimal:
    """Decode fixed-point nanos to a decimal price for presentation/domain use."""
    return Decimal(price_nanos) / PRICE_NANOS_SCALE


def market_trade_from_storage(
    *,
    ts_event_ns: int,
    ts_recv_ns: int,
    price_nanos: int,
    size: int,
    side: str | None,
    sequence: int,
) -> MarketTrade:
    """Materialize a domain ``MarketTrade`` from storage-ready fields."""
    side_value = TradeSide(side) if side is not None else TradeSide.UNKNOWN
    received_at = None if ts_recv_ns == MISSING_TS_RECV_NS else utc_datetime_from_ns(ts_recv_ns)
    return MarketTrade(
        price=Price(decimal_price_from_nanos(price_nanos)),
        size=Volume(size),
        event_at=utc_datetime_from_ns(ts_event_ns),
        side=side_value,
        received_at=received_at,
        trade_id=None,
        sequence=sequence if sequence >= 0 else None,
    )
