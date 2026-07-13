"""MarketTrade model tests."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketTrade, TradeSide


def _trade(
    *,
    minute: int = 0,
    side: TradeSide = TradeSide.BUY,
    received: datetime | None = None,
) -> MarketTrade:
    base = datetime(2025, 7, 13, 22, minute, tzinfo=UTC)
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=base,
        side=side,
        received_at=received,
        trade_id="t-1",
        sequence=42,
    )


def test_market_trade_accepts_valid_row() -> None:
    trade = _trade()
    assert trade.side is TradeSide.BUY
    assert trade.sequence == 42


def test_market_trade_rejects_non_positive_size() -> None:
    with pytest.raises(ValidationError, match="trade size must be positive"):
        MarketTrade(
            price=Price(Decimal("1")),
            size=Volume(0),
            event_at=datetime(2025, 7, 13, 22, 0, tzinfo=UTC),
            side=TradeSide.UNKNOWN,
        )


def test_market_trade_rejects_received_before_event() -> None:
    event_at = datetime(2025, 7, 13, 22, 5, tzinfo=UTC)
    received_at = datetime(2025, 7, 13, 22, 4, tzinfo=UTC)
    with pytest.raises(ValidationError, match="received_at must not be before event_at"):
        MarketTrade(
            price=Price(Decimal("1")),
            size=Volume(1),
            event_at=event_at,
            received_at=received_at,
            side=TradeSide.SELL,
        )
