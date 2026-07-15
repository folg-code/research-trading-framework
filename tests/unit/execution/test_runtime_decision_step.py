"""Tests for one-step dry-run runtime orchestration."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.types import Price
from trading_framework.execution import (
    BestBidAskSnapshot,
    ExecutionEvent,
    ExecutionEventType,
    LocalExecutionRuntimeSession,
    PaperBroker,
    RuntimeDecisionStep,
    StrategyModelOrderAdapter,
)
from trading_framework.strategy import (
    BTC_FUTURES_DEMO_DISCLOSURE,
    build_btc_futures_demo_strategy_model,
)
from trading_framework.time.clocks.fixed import FixedClock

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class InMemoryEventSink:
    events: list[ExecutionEvent] = field(default_factory=list)

    def append(self, event: ExecutionEvent) -> None:
        self.events.append(event)


def _quote() -> BestBidAskSnapshot:
    return BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )


def _broker() -> PaperBroker:
    return PaperBroker(
        account_id="paper-btc",
        symbol="BTCUSDT",
        currency="USDT",
        starting_equity=Decimal("10000"),
    )


def _step(
    *,
    sink: InMemoryEventSink,
    broker: PaperBroker,
) -> RuntimeDecisionStep:
    return RuntimeDecisionStep(
        session=LocalExecutionRuntimeSession(
            runtime_id="btc-dry-run-local",
            provider="binance_usdm",
            symbol="BTCUSDT",
            event_sink=sink,
            clock=FixedClock(NOW),
        ),
        strategy_adapter=StrategyModelOrderAdapter(
            strategy_model=build_btc_futures_demo_strategy_model(),
            symbol="BTCUSDT",
            disclosure=BTC_FUTURES_DEMO_DISCLOSURE,
        ),
        broker=broker,
    )


def test_runtime_decision_step_submits_order_and_records_lifecycle_events() -> None:
    sink = InMemoryEventSink()
    broker = _broker()
    position = broker.initial_state(NOW).position

    result = _step(sink=sink, broker=broker).run(
        entry_signal_active=True,
        exit_signal_active=False,
        position=position,
        quote=_quote(),
    )

    assert result.order_submitted
    assert result.broker_result is not None
    assert result.broker_result.position.quantity == Decimal("0.001")
    assert [event.event_type for event in sink.events] == [
        ExecutionEventType.MARKET_EVENT_RECEIVED,
        ExecutionEventType.ORDER_INTENT_CREATED,
        ExecutionEventType.SIMULATED_ORDER_FILLED,
        ExecutionEventType.POSITION_UPDATED,
    ]
    assert all(event.payload is not None for event in sink.events)
    assert {event.payload["simulated"] for event in sink.events if event.payload is not None} == {
        "true"
    }


def test_runtime_decision_step_holds_without_order_when_signal_is_inactive() -> None:
    sink = InMemoryEventSink()
    broker = _broker()
    position = broker.initial_state(NOW).position

    result = _step(sink=sink, broker=broker).run(
        entry_signal_active=False,
        exit_signal_active=False,
        position=position,
        quote=_quote(),
    )

    assert not result.order_submitted
    assert result.broker_result is None
    assert [event.event_type for event in sink.events] == [ExecutionEventType.MARKET_EVENT_RECEIVED]
    assert sink.events[0].payload is not None
    assert sink.events[0].payload["current_signal"] == "no_signal"
