"""Tests for dry-run paper broker accounting."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    BestBidAskSnapshot,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperAccountSnapshot,
    PaperBroker,
    PaperPosition,
    PositionSide,
)

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _quote(
    bid: str = "65000",
    ask: str = "65010",
    *,
    event_at: datetime = NOW,
) -> BestBidAskSnapshot:
    return BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal(bid)),
        ask_price=Price(Decimal(ask)),
        event_at=event_at,
    )


def _intent(side: OrderSide, quantity: str, *, requested_at: datetime = NOW) -> OrderIntent:
    return OrderIntent(
        intent_id=f"intent-{side.value}-{quantity}",
        strategy_id="demo-momentum",
        symbol="BTCUSDT",
        side=side,
        order_type=OrderType.MARKET,
        quantity=Decimal(quantity),
        requested_at=requested_at,
        reason="unit test",
    )


def test_paper_broker_initial_state_is_flat_and_simulated() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )

    state = broker.initial_state(NOW)

    assert state.position.side is PositionSide.FLAT
    assert state.position.quantity == Decimal("0")
    assert state.position.simulated
    assert state.account.equity == Decimal("10000")
    assert state.account.simulated


def test_paper_broker_fills_buy_at_ask_and_marks_position() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )

    result = broker.accept_market_order(_intent(OrderSide.BUY, "0.10"), _quote())

    assert result.order.status is OrderStatus.SIMULATED_FILLED
    assert result.order.simulated
    assert result.fill.price.value == Decimal("65010")
    assert result.fill.simulated
    assert result.position.side is PositionSide.LONG
    assert result.position.quantity == Decimal("0.10")
    assert result.position.average_entry_price == Price(Decimal("65010"))
    assert result.account.realized_pnl == Decimal("0")


def test_paper_broker_marks_long_unrealized_pnl() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    broker.accept_market_order(_intent(OrderSide.BUY, "0.10"), _quote())

    state = broker.mark_to_market(Price(Decimal("65110")), NOW)

    assert state.position.unrealized_pnl == Decimal("10.00")
    assert state.account.unrealized_pnl == Decimal("10.00")
    assert state.account.equity == Decimal("10010.00")


def test_paper_broker_restores_position_and_marks_to_market() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    account = PaperAccountSnapshot(
        account_id="paper-btc",
        currency="USDT",
        starting_equity=Decimal("10000"),
        realized_pnl=Decimal("5"),
        unrealized_pnl=Decimal("10"),
        equity=Decimal("10015"),
        updated_at=NOW,
    )
    position = PaperPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.10"),
        average_entry_price=Price(Decimal("65000")),
        mark_price=Price(Decimal("65100")),
        unrealized_pnl=Decimal("10"),
        updated_at=NOW,
    )

    restored = broker.restore_state(
        account=account,
        position=position,
        order_sequence=3,
        fill_sequence=4,
    )
    marked = broker.mark_to_market(Price(Decimal("65200")), NOW)
    result = broker.accept_market_order(_intent(OrderSide.BUY, "0.01"), _quote())

    assert restored.position == position
    assert restored.account == account
    assert marked.position.quantity == Decimal("0.10")
    assert marked.position.average_entry_price == Price(Decimal("65000"))
    assert marked.account.realized_pnl == Decimal("5")
    assert marked.account.unrealized_pnl == Decimal("20.00")
    assert marked.account.equity == Decimal("10025.00")
    assert result.order.order_id == "paper-order-4"
    assert result.fill.fill_id == "paper-fill-5"


def test_paper_broker_closes_long_and_realizes_pnl() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    broker.accept_market_order(_intent(OrderSide.BUY, "0.10"), _quote())

    result = broker.accept_market_order(
        _intent(OrderSide.SELL, "0.10"),
        _quote(bid="65100", ask="65110"),
    )

    assert result.fill.price.value == Decimal("65100")
    assert result.position.side is PositionSide.FLAT
    assert result.position.quantity == Decimal("0")
    assert result.account.realized_pnl == Decimal("9.00")
    assert result.account.unrealized_pnl == Decimal("0")
    assert result.account.equity == Decimal("10009.00")


def test_paper_broker_reverses_long_to_short() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    broker.accept_market_order(_intent(OrderSide.BUY, "0.10"), _quote())

    result = broker.accept_market_order(
        _intent(OrderSide.SELL, "0.25"),
        _quote(bid="65100", ask="65110"),
    )

    assert result.position.side is PositionSide.SHORT
    assert result.position.quantity == Decimal("0.15")
    assert result.position.average_entry_price == Price(Decimal("65100"))
    assert result.account.realized_pnl == Decimal("9.00")


def test_paper_broker_rejects_symbol_mismatch() -> None:
    broker = PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )
    quote = BestBidAskSnapshot(
        symbol="ETHUSDT",
        bid_price=Price(Decimal("3000")),
        ask_price=Price(Decimal("3001")),
        event_at=NOW,
    )

    with pytest.raises(ValidationError, match="quote symbol"):
        broker.accept_market_order(_intent(OrderSide.BUY, "0.10"), quote)
