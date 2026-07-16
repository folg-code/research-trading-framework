"""Tests for adapting Strategy Models into dry-run order intents."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    OrderSide,
    PaperPosition,
    PositionSide,
    StrategyModelOrderAdapter,
    StrategyOrderDecisionType,
)
from trading_framework.strategy import (
    BTC_FUTURES_DEMO_DISCLOSURE,
    build_btc_futures_demo_strategy_model,
)

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _position(side: PositionSide, quantity: str = "0", symbol: str = "BTCUSDT") -> PaperPosition:
    average_entry_price = Price(Decimal("65000")) if side is not PositionSide.FLAT else None
    mark_price = Price(Decimal("65100")) if side is not PositionSide.FLAT else None
    return PaperPosition(
        symbol=symbol,
        side=side,
        quantity=Decimal(quantity),
        average_entry_price=average_entry_price,
        mark_price=mark_price,
        unrealized_pnl=Decimal("0"),
        updated_at=NOW,
    )


def _adapter() -> StrategyModelOrderAdapter:
    return StrategyModelOrderAdapter(
        strategy_model=build_btc_futures_demo_strategy_model(),
        symbol="BTCUSDT",
        disclosure=BTC_FUTURES_DEMO_DISCLOSURE,
    )


def test_strategy_model_order_adapter_enters_long_from_flat_signal() -> None:
    decision = _adapter().decide(
        entry_signal_active=True,
        exit_signal_active=False,
        position=_position(PositionSide.FLAT),
        requested_at=NOW,
    )

    assert decision.decision_type is StrategyOrderDecisionType.ENTER_LONG
    assert decision.order_intent is not None
    assert decision.order_intent.strategy_id == "btc_futures_demo_ema_momentum"
    assert decision.order_intent.side is OrderSide.BUY
    assert decision.order_intent.quantity == Decimal("0.001")
    assert decision.order_intent.reason is not None
    assert "simulated dry-run" in decision.order_intent.reason
    assert "unvalidated demo" in decision.order_intent.reason


def test_strategy_model_order_adapter_holds_long_until_exit_signal() -> None:
    decision = _adapter().decide(
        entry_signal_active=True,
        exit_signal_active=False,
        position=_position(PositionSide.LONG, "0.001"),
        requested_at=NOW,
    )

    assert decision.decision_type is StrategyOrderDecisionType.HOLD
    assert decision.reason == "long_without_exit_signal"
    assert decision.order_intent is None


def test_strategy_model_order_adapter_flattens_long_on_exit_signal() -> None:
    decision = _adapter().decide(
        entry_signal_active=False,
        exit_signal_active=True,
        position=_position(PositionSide.LONG, "0.002"),
        requested_at=NOW,
    )

    assert decision.decision_type is StrategyOrderDecisionType.FLATTEN_LONG
    assert decision.order_intent is not None
    assert decision.order_intent.side is OrderSide.SELL
    assert decision.order_intent.quantity == Decimal("0.002")


def test_strategy_model_order_adapter_rejects_symbol_mismatch() -> None:
    with pytest.raises(ValidationError, match="position symbol"):
        _adapter().decide(
            entry_signal_active=True,
            exit_signal_active=False,
            position=_position(PositionSide.FLAT, symbol="ETHUSDT"),
            requested_at=NOW,
        )
