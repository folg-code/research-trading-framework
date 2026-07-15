"""Tests for dry-run fill reference helpers."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.execution import (
    OrderIntent,
    OrderSide,
    OrderType,
    PaperBroker,
    closed_bar_close_reference_quote,
)
from trading_framework.market.models import MarketBar

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _bar(close: str = "65000") -> MarketBar:
    close_price = Price(Decimal(close))
    return MarketBar(
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Volume(1),
        observed_at=NOW,
        available_at=NOW + timedelta(minutes=1),
    )


def test_closed_bar_close_reference_quote_uses_close_as_zero_spread_reference() -> None:
    bar = _bar("65010")

    quote = closed_bar_close_reference_quote(symbol="BTCUSDT", bar=bar)

    assert quote.symbol == "BTCUSDT"
    assert quote.bid_price == Price(Decimal("65010"))
    assert quote.ask_price == Price(Decimal("65010"))
    assert quote.event_at == bar.available_at
    assert quote.received_at == bar.available_at


def test_closed_bar_close_reference_quote_can_fill_paper_market_order() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    intent = OrderIntent(
        intent_id="intent-1",
        strategy_id="btc_futures_demo_ema_momentum",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
        requested_at=NOW,
        reason="unit test",
    )

    result = broker.accept_market_order(
        intent,
        closed_bar_close_reference_quote(symbol="BTCUSDT", bar=_bar("65010")),
    )

    assert result.fill.price == Price(Decimal("65010"))
    assert result.position.quantity == Decimal("0.001")
