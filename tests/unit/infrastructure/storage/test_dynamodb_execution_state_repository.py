"""Tests for the DynamoDB execution state repository adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.core.types.volume import Volume
from trading_framework.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionMode,
    ExecutionReadModelQuery,
    ExecutionStateRepository,
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
from trading_framework.infrastructure.storage.dynamodb_execution_state import (
    DynamoDbExecutionStateRepository,
)
from trading_framework.market.models import MarketBar

NOW = datetime(2026, 7, 16, 8, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


@dataclass(slots=True)
class FakeDynamoDbClient:
    items: dict[tuple[str, str, str], dict[str, dict[str, str]]]

    def get_item(
        self,
        *,
        TableName: str,
        Key: Mapping[str, Mapping[str, str]],
        ConsistentRead: bool = False,
    ) -> Mapping[str, Any]:
        assert ConsistentRead is True
        pk = Key["pk"]["S"]
        sk = Key["sk"]["S"]
        item = self.items.get((TableName, pk, sk))
        return {"Item": item} if item is not None else {}

    def put_item(
        self,
        *,
        TableName: str,
        Item: Mapping[str, Mapping[str, str]],
    ) -> Mapping[str, Any]:
        pk = Item["pk"]["S"]
        sk = Item["sk"]["S"]
        self.items[(TableName, pk, sk)] = {name: dict(value) for name, value in Item.items()}
        return {}


def test_dynamodb_execution_state_repository_round_trips_latest_status() -> None:
    client = FakeDynamoDbClient(items={})
    repository: ExecutionStateRepository = DynamoDbExecutionStateRepository(
        client=client,
        table_name="execution-state",
        clock=FixedClock(NOW + timedelta(seconds=30)),
        recent_event_limit=2,
        recent_order_limit=2,
        recent_fill_limit=2,
    )

    repository.save_runtime_status(_status())
    repository.save_position("runtime-1", _position())
    repository.save_account("runtime-1", _account())
    repository.save_order("runtime-1", _order("order-1", NOW))
    repository.save_order("runtime-1", _order("order-2", NOW + timedelta(seconds=1)))
    repository.save_fill("runtime-1", _fill("fill-1", "order-1", NOW))
    repository.save_fill("runtime-1", _fill("fill-2", "order-2", NOW + timedelta(seconds=1)))
    repository.save_bar("runtime-1", _bar(NOW - timedelta(minutes=2), "65000"))
    repository.save_bar("runtime-1", _bar(NOW - timedelta(minutes=1), "65010"))
    repository.append_event("runtime-1", _event("event-1", NOW))
    repository.append_event("runtime-1", _event("event-2", NOW + timedelta(seconds=1)))
    repository.append_event("runtime-1", _event("event-3", NOW + timedelta(seconds=2)))

    view = repository.latest_status_view(
        ExecutionReadModelQuery(
            runtime_id="runtime-1",
            recent_event_limit=2,
            recent_order_limit=1,
            recent_fill_limit=1,
        )
    )

    assert view is not None
    assert view.runtime_id == "runtime-1"
    assert view.mode is ExecutionMode.DRY_RUN
    assert view.provider == "binance_usdm"
    assert view.symbol == "BTCUSDT"
    assert view.status is RuntimeHealth.RUNNING
    assert view.generated_at == NOW + timedelta(seconds=30)
    assert view.last_price == Price(Decimal("65010"))
    assert view.current_position == _position()
    assert view.paper_equity == Decimal("10010")
    assert [order.order_id for order in view.recent_orders] == ["order-2"]
    assert [fill.fill_id for fill in view.recent_fills] == ["fill-2"]
    assert [bar.close for bar in view.recent_bars] == [
        Price(Decimal("65000")),
        Price(Decimal("65010")),
    ]
    assert [event.event_id for event in view.recent_events] == ["event-2", "event-3"]


def test_dynamodb_execution_state_repository_writes_expected_state_item() -> None:
    client = FakeDynamoDbClient(items={})
    repository = DynamoDbExecutionStateRepository(
        client=client,
        table_name="execution-state",
        clock=FixedClock(NOW),
    )

    repository.save_runtime_status(_status())
    repository.append_event("runtime-1", _event("event-1", NOW))
    repository.save_bar("runtime-1", _bar(NOW - timedelta(minutes=1), "65010"))

    item = client.items[("execution-state", "RUNTIME#runtime-1", "STATE")]
    state_payload = json.loads(item["state_json"]["S"])

    assert item["runtime_id"]["S"] == "runtime-1"
    assert item["version"]["N"] == "1"
    assert item["updated_at"]["S"] == NOW.isoformat()
    assert state_payload["version"] == 1
    assert state_payload["status"]["runtime_id"] == "runtime-1"
    assert state_payload["bars"][0]["close"] == "65010"
    assert state_payload["events"][0]["event_type"] == ExecutionEventType.HEARTBEAT_RECORDED.value
    assert state_payload["events"][0]["simulated"] is True


def test_dynamodb_execution_state_repository_returns_empty_for_unknown_runtime() -> None:
    repository = DynamoDbExecutionStateRepository(
        client=FakeDynamoDbClient(items={}),
        table_name="execution-state",
    )

    assert repository.recent_events(ExecutionReadModelQuery(runtime_id="missing-runtime")) == ()
    assert (
        repository.latest_status_view(ExecutionReadModelQuery(runtime_id="missing-runtime")) is None
    )


def test_dynamodb_execution_state_repository_rejects_invalid_configuration() -> None:
    with pytest.raises(ValidationError, match="table_name"):
        DynamoDbExecutionStateRepository(
            client=FakeDynamoDbClient(items={}),
            table_name=" ",
        )
    with pytest.raises(ValidationError, match="recent_event_limit"):
        DynamoDbExecutionStateRepository(
            client=FakeDynamoDbClient(items={}),
            table_name="execution-state",
            recent_event_limit=0,
        )


def _status() -> RuntimeStatusSnapshot:
    return RuntimeStatusSnapshot(
        runtime_id="runtime-1",
        mode=ExecutionMode.DRY_RUN,
        status=RuntimeHealth.RUNNING,
        provider="binance_usdm",
        symbol="BTCUSDT",
        last_heartbeat_at=NOW,
        last_market_event_at=NOW - timedelta(seconds=5),
        current_signal="entry_signal_active",
    )


def _event(event_id: str, occurred_at: datetime) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=event_id,
        event_type=ExecutionEventType.HEARTBEAT_RECORDED,
        occurred_at=occurred_at,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
        payload={"runtime_id": "runtime-1", "simulated": "true"},
    )


def _order(order_id: str, created_at: datetime) -> SimulatedOrder:
    return SimulatedOrder(
        order_id=order_id,
        intent_id=f"intent-{order_id}",
        strategy_id="strategy-1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
        status=OrderStatus.SIMULATED_FILLED,
        created_at=created_at,
    )


def _fill(fill_id: str, order_id: str, filled_at: datetime) -> SimulatedFill:
    return SimulatedFill(
        fill_id=fill_id,
        order_id=order_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Price(Decimal("65000")),
        filled_at=filled_at,
    )


def _bar(observed_at: datetime, close: str) -> MarketBar:
    return MarketBar(
        open=Price(Decimal("65000")),
        high=Price(Decimal("65020")),
        low=Price(Decimal("64990")),
        close=Price(Decimal(close)),
        volume=Volume(100),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _position() -> PaperPosition:
    return PaperPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.001"),
        average_entry_price=Price(Decimal("65000")),
        mark_price=Price(Decimal("65010")),
        unrealized_pnl=Decimal("10"),
        updated_at=NOW,
    )


def _account() -> PaperAccountSnapshot:
    return PaperAccountSnapshot(
        account_id="paper-btc",
        currency="USDT",
        starting_equity=Decimal("10000"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("10"),
        equity=Decimal("10010"),
        updated_at=NOW,
    )
