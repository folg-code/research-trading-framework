"""Execution domain protocols."""

from typing import Protocol

from trading_framework.execution.models import ExecutionEvent, RuntimeStatusSnapshot


class ExecutionEventSink(Protocol):
    """Append-only sink for execution runtime events."""

    def append(self, event: ExecutionEvent) -> None:
        """Persist or publish one execution event."""


class RuntimeStatusReader(Protocol):
    """Read-only runtime status query port."""

    def latest_status(self, runtime_id: str) -> RuntimeStatusSnapshot | None:
        """Return the latest runtime status snapshot, if present."""
