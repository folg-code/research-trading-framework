"""Tests for execution read-model contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import MappingProxyType

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
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
    RecentBarView,
    RecentExecutionEventView,
    RecentFillView,
    RecentOrderView,
    RuntimeHealth,
    RuntimeStatusSnapshot,
    RuntimeStatusView,
    SimulatedFill,
    SimulatedOrder,
)
from trading_framework.market.models import MarketBar

NOW = datetime(2026, 7, 16, 8, 0, tzinfo=UTC)


@dataclass(slots=True)
class FakeExecutionStateRepository:
    events: list[RecentExecutionEventView] = field(default_factory=list)
    status_view: RuntimeStatusView | None = None
    orders: list[RecentOrderView] = field(default_factory=list)
    fills: list[RecentFillView] = field(default_factory=list)
    bars: list[RecentBarView] = field(default_factory=list)
    position: PaperPosition | None = None
    account: PaperAccountSnapshot | None = None

    def append_event(self, runtime_id: str, event: ExecutionEvent) -> None:
        assert runtime_id == "runtime-1"
        self.events.append(RecentExecutionEventView.from_event(event))

    def save_runtime_status(self, status: RuntimeStatusSnapshot) -> None:
        self.status_view = RuntimeStatusView(
            runtime_id=status.runtime_id,
            mode=status.mode,
            provider=status.provider,
            symbol=status.symbol,
            status=status.status,
            generated_at=NOW,
            last_heartbeat_at=status.last_heartbeat_at,
            last_market_event_at=status.last_market_event_at,
            current_signal=status.current_signal,
        )

    def save_order(self, runtime_id: str, order: SimulatedOrder) -> None:
        assert runtime_id == "runtime-1"
        self.orders.append(
            RecentOrderView(
                order_id=order.order_id,
                intent_id=order.intent_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                status=order.status,
                created_at=order.created_at,
            )
        )

    def save_fill(self, runtime_id: str, fill: SimulatedFill) -> None:
        assert runtime_id == "runtime-1"
        self.fills.append(
            RecentFillView(
                fill_id=fill.fill_id,
                order_id=fill.order_id,
                symbol=fill.symbol,
                side=fill.side,
                quantity=fill.quantity,
                price=fill.price,
                filled_at=fill.filled_at,
                liquidity=fill.liquidity,
            )
        )

    def save_position(self, runtime_id: str, position: PaperPosition) -> None:
        assert runtime_id == "runtime-1"
        self.position = position

    def save_account(self, runtime_id: str, account: PaperAccountSnapshot) -> None:
        assert runtime_id == "runtime-1"
        self.account = account

    def save_bar(self, runtime_id: str, bar: MarketBar) -> None:
        assert runtime_id == "runtime-1"
        self.bars.append(
            RecentBarView(
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                observed_at=bar.observed_at,
                available_at=bar.available_at,
            )
        )

    def latest_status_view(self, query: ExecutionReadModelQuery) -> RuntimeStatusView | None:
        assert query.runtime_id == "runtime-1"
        return self.status_view

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[RecentExecutionEventView, ...]:
        assert query.runtime_id == "runtime-1"
        return tuple(self.events[-query.recent_event_limit :])

    def recent_bars(self, query: ExecutionReadModelQuery) -> tuple[RecentBarView, ...]:
        assert query.runtime_id == "runtime-1"
        return tuple(self.bars[-query.recent_bar_limit :])


def test_execution_read_model_query_validates_positive_limits() -> None:
    query = ExecutionReadModelQuery(
        runtime_id=" runtime-1 ",
        recent_event_limit=10,
        recent_order_limit=5,
        recent_fill_limit=3,
    )

    assert query.runtime_id == "runtime-1"

    with pytest.raises(ValidationError, match="recent_event_limit"):
        ExecutionReadModelQuery(runtime_id="runtime-1", recent_event_limit=0)


def test_recent_execution_event_view_from_event_is_immutable() -> None:
    event = ExecutionEvent(
        event_id="event-1",
        event_type=ExecutionEventType.MARKET_EVENT_RECEIVED,
        occurred_at=NOW,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
        payload={"current_signal": "entry_signal_active"},
    )

    view = RecentExecutionEventView.from_event(event)

    assert view.event_id == "event-1"
    assert view.payload is not None
    assert isinstance(view.payload, MappingProxyType)


def test_runtime_status_view_tracks_freshness_and_simulated_marker() -> None:
    view = RuntimeStatusView(
        runtime_id="runtime-1",
        mode=ExecutionMode.DRY_RUN,
        provider="binance_usdm",
        symbol="BTCUSDT",
        status=RuntimeHealth.RUNNING,
        generated_at=NOW,
        last_heartbeat_at=NOW - timedelta(seconds=20),
        last_market_event_at=NOW - timedelta(seconds=30),
        last_price=Price(Decimal("65000")),
        current_position=_position(),
        paper_equity=Decimal("10010"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("10"),
        recent_orders=(_order_view(),),
        recent_fills=(_fill_view(),),
    )

    assert not view.is_stale(reference_time=NOW, stale_after=timedelta(seconds=30))
    assert view.is_stale(reference_time=NOW, stale_after=timedelta(seconds=10))

    with pytest.raises(ValidationError, match="simulated"):
        RuntimeStatusView(
            runtime_id="runtime-1",
            mode=ExecutionMode.DRY_RUN,
            provider="binance_usdm",
            symbol="BTCUSDT",
            status=RuntimeHealth.RUNNING,
            generated_at=NOW,
            last_heartbeat_at=NOW,
            simulated=False,
        )


def test_execution_state_repository_protocol_shape() -> None:
    repository: ExecutionStateRepository = FakeExecutionStateRepository()
    repository.append_event("runtime-1", _event())
    repository.save_runtime_status(_status())
    repository.save_order("runtime-1", _order())
    repository.save_fill("runtime-1", _fill())
    repository.save_position("runtime-1", _position())
    repository.save_account("runtime-1", _account())
    repository.save_bar("runtime-1", _bar())

    query = ExecutionReadModelQuery(runtime_id="runtime-1", recent_event_limit=1)
    status_view = repository.latest_status_view(query)
    recent_events = repository.recent_events(query)
    recent_bars = repository.recent_bars(query)

    assert status_view is not None
    assert status_view.status is RuntimeHealth.RUNNING
    assert [event.event_id for event in recent_events] == ["event-1"]
    assert [bar.close for bar in recent_bars] == [Price(Decimal("65010"))]


def _event() -> ExecutionEvent:
    return ExecutionEvent(
        event_id="event-1",
        event_type=ExecutionEventType.HEARTBEAT_RECORDED,
        occurred_at=NOW,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
    )


def _status() -> RuntimeStatusSnapshot:
    return RuntimeStatusSnapshot(
        runtime_id="runtime-1",
        mode=ExecutionMode.DRY_RUN,
        status=RuntimeHealth.RUNNING,
        provider="binance_usdm",
        symbol="BTCUSDT",
        last_heartbeat_at=NOW,
    )


def _order() -> SimulatedOrder:
    return SimulatedOrder(
        order_id="order-1",
        intent_id="intent-1",
        strategy_id="strategy-1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
        status=OrderStatus.SIMULATED_FILLED,
        created_at=NOW,
    )


def _fill() -> SimulatedFill:
    return SimulatedFill(
        fill_id="fill-1",
        order_id="order-1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Price(Decimal("65000")),
        filled_at=NOW,
    )


def _bar() -> MarketBar:
    return MarketBar(
        open=Price(Decimal("65000")),
        high=Price(Decimal("65020")),
        low=Price(Decimal("64990")),
        close=Price(Decimal("65010")),
        volume=Volume(100),
        observed_at=NOW,
        available_at=NOW + timedelta(minutes=1),
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


def _order_view() -> RecentOrderView:
    order = _order()
    return RecentOrderView(
        order_id=order.order_id,
        intent_id=order.intent_id,
        strategy_id=order.strategy_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        status=order.status,
        created_at=order.created_at,
    )


def _fill_view() -> RecentFillView:
    fill = _fill()
    return RecentFillView(
        fill_id=fill.fill_id,
        order_id=fill.order_id,
        symbol=fill.symbol,
        side=fill.side,
        quantity=fill.quantity,
        price=fill.price,
        filled_at=fill.filled_at,
        liquidity=fill.liquidity,
    )
