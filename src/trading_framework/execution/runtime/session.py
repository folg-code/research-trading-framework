"""Local dry-run runtime session lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.models import (
    ExecutionEvent,
    ExecutionEventType,
    Heartbeat,
    RuntimeHealth,
    RuntimeStatusSnapshot,
)
from trading_framework.execution.modes import ExecutionMode
from trading_framework.execution.protocols import ExecutionEventSink
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.utc_instant import require_utc_aware


@final
@dataclass(slots=True)
class LocalExecutionRuntimeSession:
    """Track local dry-run lifecycle state and emit execution events."""

    runtime_id: str
    provider: str
    symbol: str
    event_sink: ExecutionEventSink
    clock: Clock = field(default_factory=SystemClock)

    _event_sequence: int = 0
    _latest_status: RuntimeStatusSnapshot | None = None
    _last_market_event_at: datetime | None = None
    _current_signal: str | None = None

    def start(self) -> RuntimeStatusSnapshot:
        """Mark the runtime as running and emit a start event."""
        status = self._status(RuntimeHealth.RUNNING)
        self._emit(
            ExecutionEventType.RUNTIME_STARTED,
            payload={
                "runtime_id": self.runtime_id,
                "provider": self.provider,
                "status": status.status.value,
                "simulated": "true",
            },
        )
        return status

    def record_market_event(
        self,
        *,
        event_at: datetime,
        current_signal: str | None = None,
    ) -> RuntimeStatusSnapshot:
        """Record that a provider-independent market event was consumed."""
        timestamp = require_utc_aware(event_at)
        self._last_market_event_at = timestamp
        if current_signal is not None:
            self._current_signal = current_signal
        status = self._status(RuntimeHealth.RUNNING)
        payload = {
            "runtime_id": self.runtime_id,
            "event_at": timestamp.isoformat(),
            "simulated": "true",
        }
        if self._current_signal is not None:
            payload["current_signal"] = self._current_signal
        self._emit(ExecutionEventType.MARKET_EVENT_RECEIVED, payload=payload)
        return status

    def record_heartbeat(
        self,
        *,
        status: RuntimeHealth = RuntimeHealth.RUNNING,
        message: str | None = None,
    ) -> Heartbeat:
        """Emit a heartbeat and update the latest runtime status."""
        now = self.clock.now()
        heartbeat = Heartbeat(
            runtime_id=self.runtime_id,
            recorded_at=now,
            status=status,
            message=message,
        )
        self._status(status)
        payload = {
            "runtime_id": self.runtime_id,
            "status": status.value,
            "simulated": "true",
        }
        if message is not None:
            payload["message"] = message
        self._emit(ExecutionEventType.HEARTBEAT_RECORDED, payload=payload)
        return heartbeat

    def stop(self, *, message: str | None = None) -> RuntimeStatusSnapshot:
        """Mark the runtime as stopped and emit a stop event."""
        status = self._status(RuntimeHealth.STOPPED)
        payload = {
            "runtime_id": self.runtime_id,
            "status": status.status.value,
            "simulated": "true",
        }
        if message is not None:
            payload["message"] = message
        self._emit(ExecutionEventType.RUNTIME_STOPPED, payload=payload)
        return status

    def fail(self, *, message: str) -> RuntimeStatusSnapshot:
        """Mark the runtime as failed and emit a failure event."""
        if not message.strip():
            msg = "failure message must be non-empty"
            raise ValidationError(msg)
        status = self._status(RuntimeHealth.FAILED)
        self._emit(
            ExecutionEventType.RUNTIME_FAILED,
            payload={
                "runtime_id": self.runtime_id,
                "status": status.status.value,
                "message": message,
                "simulated": "true",
            },
        )
        return status

    def latest_status(self, runtime_id: str) -> RuntimeStatusSnapshot | None:
        """Return the latest status for this runtime id."""
        if runtime_id != self.runtime_id:
            return None
        return self._latest_status

    def _status(self, status: RuntimeHealth) -> RuntimeStatusSnapshot:
        snapshot = RuntimeStatusSnapshot(
            runtime_id=self.runtime_id,
            mode=ExecutionMode.DRY_RUN,
            status=status,
            provider=self.provider,
            symbol=self.symbol,
            last_heartbeat_at=self.clock.now(),
            last_market_event_at=self._last_market_event_at,
            current_signal=self._current_signal,
        )
        self._latest_status = snapshot
        return snapshot

    def _emit(
        self,
        event_type: ExecutionEventType,
        *,
        payload: dict[str, str] | None = None,
    ) -> ExecutionEvent:
        self._event_sequence += 1
        event = ExecutionEvent(
            event_id=f"{self.runtime_id}-{self._event_sequence:06d}-{event_type.value}",
            event_type=event_type,
            occurred_at=self.clock.now(),
            mode=ExecutionMode.DRY_RUN.value,
            symbol=self.symbol,
            payload=payload,
        )
        self.event_sink.append(event)
        return event
