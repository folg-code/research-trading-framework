"""Tests for local dry-run runtime session lifecycle."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    BestBidAskSnapshot,
    ExecutionEvent,
    ExecutionEventType,
    LocalExecutionRuntimeSession,
    OrderIntent,
    OrderSide,
    OrderType,
    PaperBroker,
    RuntimeHealth,
)
from trading_framework.time.clocks.fixed import FixedClock

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class InMemoryEventSink:
    events: list[ExecutionEvent] = field(default_factory=list)

    def append(self, event: ExecutionEvent) -> None:
        self.events.append(event)


def _session(sink: InMemoryEventSink) -> LocalExecutionRuntimeSession:
    return LocalExecutionRuntimeSession(
        runtime_id="btc-dry-run-local",
        provider="binance_usdm",
        symbol="BTCUSDT",
        event_sink=sink,
        clock=FixedClock(NOW),
    )


def test_runtime_session_start_emits_running_status_and_event() -> None:
    sink = InMemoryEventSink()

    status = _session(sink).start()

    assert status.status is RuntimeHealth.RUNNING
    assert status.simulated
    assert sink.events[0].event_type is ExecutionEventType.RUNTIME_STARTED
    assert sink.events[0].event_id == "btc-dry-run-local-000001-runtime_started"
    assert sink.events[0].payload is not None
    assert sink.events[0].payload["simulated"] == "true"


def test_runtime_session_records_market_event_and_latest_status() -> None:
    sink = InMemoryEventSink()
    session = _session(sink)
    session.start()
    market_event_at = NOW + timedelta(seconds=5)

    status = session.record_market_event(
        event_at=market_event_at,
        current_signal="entry_signal_active",
    )

    assert status.last_market_event_at == market_event_at
    assert status.current_signal == "entry_signal_active"
    assert session.latest_status("btc-dry-run-local") == status
    assert session.latest_status("other-runtime") is None
    assert sink.events[-1].event_type is ExecutionEventType.MARKET_EVENT_RECEIVED
    assert sink.events[-1].payload is not None
    assert sink.events[-1].payload["current_signal"] == "entry_signal_active"


def test_runtime_session_records_heartbeat_and_stop_events() -> None:
    sink = InMemoryEventSink()
    session = _session(sink)
    session.start()

    heartbeat = session.record_heartbeat(message="alive")
    stopped = session.stop(message="bounded run complete")

    assert heartbeat.status is RuntimeHealth.RUNNING
    assert heartbeat.message == "alive"
    assert stopped.status is RuntimeHealth.STOPPED
    assert [event.event_type for event in sink.events] == [
        ExecutionEventType.RUNTIME_STARTED,
        ExecutionEventType.HEARTBEAT_RECORDED,
        ExecutionEventType.RUNTIME_STOPPED,
    ]


def test_runtime_session_records_order_fill_and_position_events() -> None:
    sink = InMemoryEventSink()
    session = _session(sink)
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
        reason="simulated dry-run order intent",
    )
    quote = BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )

    order_event = session.record_order_intent(intent)
    fill_event, position_event = session.record_broker_result(
        broker.accept_market_order(intent, quote)
    )

    assert order_event.event_type is ExecutionEventType.ORDER_INTENT_CREATED
    assert order_event.correlation_id == "intent-1"
    assert order_event.payload is not None
    assert order_event.payload["simulated"] == "true"
    assert fill_event.event_type is ExecutionEventType.SIMULATED_ORDER_FILLED
    assert fill_event.correlation_id == "intent-1"
    assert fill_event.payload is not None
    assert fill_event.payload["price"] == "65010"
    assert position_event.event_type is ExecutionEventType.POSITION_UPDATED
    assert position_event.payload is not None
    assert position_event.payload["side"] == "long"
    assert position_event.payload["equity"] == "10000.000"


def test_runtime_session_fail_requires_message() -> None:
    sink = InMemoryEventSink()
    session = _session(sink)

    with pytest.raises(ValidationError, match="failure message"):
        session.fail(message=" ")

    failed = session.fail(message="feed exhausted")

    assert failed.status is RuntimeHealth.FAILED
    assert sink.events[-1].event_type is ExecutionEventType.RUNTIME_FAILED
