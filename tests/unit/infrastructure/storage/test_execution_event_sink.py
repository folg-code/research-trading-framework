"""Tests for local execution event JSONL storage."""

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.execution import ExecutionEvent, ExecutionEventType, ExecutionMode
from trading_framework.execution.protocols import ExecutionEventSink
from trading_framework.infrastructure.storage import (
    JsonlExecutionEventSink,
    read_jsonl_execution_events,
)

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _event(event_id: str, *, correlation_id: str | None = None) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=event_id,
        event_type=ExecutionEventType.ORDER_INTENT_CREATED,
        occurred_at=NOW,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
        payload={"intent_id": "intent-1", "simulated": "true"},
        correlation_id=correlation_id,
    )


def test_jsonl_execution_event_sink_appends_readable_event_payloads(tmp_path: Path) -> None:
    path = tmp_path / "execution" / "events.jsonl"
    sink: ExecutionEventSink = JsonlExecutionEventSink(path)

    sink.append(_event("event-1", correlation_id="intent-1"))

    rows = read_jsonl_execution_events(path)
    assert rows == (
        {
            "event_id": "event-1",
            "event_type": "order_intent_created",
            "occurred_at": "2026-07-15T12:00:00+00:00",
            "mode": "dry_run",
            "symbol": "BTCUSDT",
            "payload": {"intent_id": "intent-1", "simulated": "true"},
            "correlation_id": "intent-1",
        },
    )


def test_jsonl_execution_event_sink_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sink = JsonlExecutionEventSink(path)

    sink.append(_event("event-1"))
    sink.append(_event("event-2"))

    rows = read_jsonl_execution_events(path)
    assert [row["event_id"] for row in rows] == ["event-1", "event-2"]


def test_read_jsonl_execution_events_returns_empty_tuple_for_missing_file(tmp_path: Path) -> None:
    assert read_jsonl_execution_events(tmp_path / "missing.jsonl") == ()
