"""Tests for local dry-run runtime session lifecycle."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution import (
    ExecutionEvent,
    ExecutionEventType,
    LocalExecutionRuntimeSession,
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


def test_runtime_session_fail_requires_message() -> None:
    sink = InMemoryEventSink()
    session = _session(sink)

    with pytest.raises(ValidationError, match="failure message"):
        session.fail(message=" ")

    failed = session.fail(message="feed exhausted")

    assert failed.status is RuntimeHealth.FAILED
    assert sink.events[-1].event_type is ExecutionEventType.RUNTIME_FAILED
