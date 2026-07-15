"""Tests for dry-run execution contracts."""

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    DRY_RUN_SAFETY_POLICY,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionMode,
    ExecutionSafetyPolicy,
    Heartbeat,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperAccountSnapshot,
    PaperPosition,
    PositionSide,
    RuntimeHealth,
    RuntimeStatusSnapshot,
    SimulatedFill,
    SimulatedOrder,
)

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def test_dry_run_safety_policy_rejects_real_orders_and_credentials() -> None:
    assert DRY_RUN_SAFETY_POLICY.mode is ExecutionMode.DRY_RUN
    assert not DRY_RUN_SAFETY_POLICY.allow_real_orders
    assert not DRY_RUN_SAFETY_POLICY.allow_exchange_credentials

    with pytest.raises(ValidationError, match="real orders"):
        ExecutionSafetyPolicy(mode=ExecutionMode.DRY_RUN, allow_real_orders=True)

    with pytest.raises(ValidationError, match="exchange credentials"):
        ExecutionSafetyPolicy(mode=ExecutionMode.DRY_RUN, allow_exchange_credentials=True)


def test_order_intent_rejects_naive_requested_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        OrderIntent(
            intent_id="intent-1",
            strategy_id="demo",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
            requested_at=datetime(2026, 7, 15, 12, 0),
        )


def test_order_and_fill_must_be_marked_simulated() -> None:
    with pytest.raises(ValidationError, match="SimulatedOrder"):
        SimulatedOrder(
            order_id="order-1",
            intent_id="intent-1",
            strategy_id="demo",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
            status=OrderStatus.CREATED,
            created_at=NOW,
            simulated=False,
        )

    with pytest.raises(ValidationError, match="SimulatedFill"):
        SimulatedFill(
            fill_id="fill-1",
            order_id="order-1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            price=Price(Decimal("65000")),
            filled_at=NOW,
            simulated=False,
        )


def test_paper_position_normalizes_flat_quantity_and_rejects_real_state() -> None:
    position = PaperPosition(
        symbol="BTCUSDT",
        side=PositionSide.FLAT,
        quantity=Decimal("0.01"),
        average_entry_price=Price(Decimal("65000")),
        mark_price=Price(Decimal("65100")),
        unrealized_pnl=Decimal("1.0"),
        updated_at=NOW,
    )

    assert position.side is PositionSide.FLAT
    assert position.quantity == Decimal("0")
    assert position.average_entry_price is None

    with pytest.raises(ValidationError, match="average_entry_price"):
        PaperPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.01"),
            average_entry_price=None,
            mark_price=Price(Decimal("65100")),
            unrealized_pnl=Decimal("1.0"),
            updated_at=NOW,
        )

    with pytest.raises(ValidationError, match="PaperPosition"):
        PaperPosition(
            symbol="BTCUSDT",
            side=PositionSide.FLAT,
            quantity=Decimal("0"),
            average_entry_price=None,
            mark_price=None,
            unrealized_pnl=Decimal("0"),
            updated_at=NOW,
            simulated=False,
        )


def test_paper_account_snapshot_rejects_real_state() -> None:
    with pytest.raises(ValidationError, match="PaperAccountSnapshot"):
        PaperAccountSnapshot(
            account_id="paper-btc",
            currency="USDT",
            starting_equity=Decimal("10000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            equity=Decimal("10000"),
            updated_at=NOW,
            simulated=False,
        )


def test_runtime_status_supports_public_health_states_and_simulated_marker() -> None:
    for health in RuntimeHealth:
        snapshot = RuntimeStatusSnapshot(
            runtime_id=f"runtime-{health.value}",
            mode=ExecutionMode.DRY_RUN,
            status=health,
            provider="binance_usdm",
            symbol="BTCUSDT",
            last_heartbeat_at=NOW,
            simulated=True,
        )
        assert snapshot.status is health
        assert snapshot.simulated

    with pytest.raises(ValidationError, match="RuntimeStatusSnapshot"):
        RuntimeStatusSnapshot(
            runtime_id="runtime-1",
            mode=ExecutionMode.DRY_RUN,
            status=RuntimeHealth.RUNNING,
            provider="binance_usdm",
            symbol="BTCUSDT",
            last_heartbeat_at=NOW,
            simulated=False,
        )


def test_execution_events_are_immutable_and_payload_read_only() -> None:
    event = ExecutionEvent(
        event_id="event-1",
        event_type=ExecutionEventType.ORDER_INTENT_CREATED,
        occurred_at=NOW,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
        payload={"intent_id": "intent-1"},
    )

    with pytest.raises(FrozenInstanceError):
        event.symbol = "ETHUSDT"  # type: ignore[misc]
    assert event.payload is not None
    with pytest.raises(TypeError):
        cast(MutableMapping[str, str], event.payload)["intent_id"] = "intent-2"


def test_heartbeat_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Heartbeat(
            runtime_id="runtime-1",
            recorded_at=datetime(2026, 7, 15, 12, 0),
            status=RuntimeHealth.RUNNING,
        )
