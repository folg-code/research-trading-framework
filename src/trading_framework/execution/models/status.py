"""Runtime status contracts for dry-run read models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import final

from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.execution.modes import ExecutionMode
from trading_framework.time.models.utc_instant import require_utc_aware


class RuntimeHealth(StrEnum):
    """Public runtime health state."""

    RUNNING = "running"
    DEGRADED = "degraded"
    STALE = "stale"
    STOPPED = "stopped"
    FAILED = "failed"


@final
@dataclass(frozen=True, slots=True)
class Heartbeat:
    """Heartbeat emitted by a dry-run runtime process."""

    runtime_id: str
    recorded_at: datetime
    status: RuntimeHealth
    message: str | None = None

    def __post_init__(self) -> None:
        recorded_at = require_utc_aware(self.recorded_at)
        if recorded_at != self.recorded_at:
            object.__setattr__(self, "recorded_at", recorded_at)
        object.__setattr__(self, "runtime_id", normalize_non_empty(self.runtime_id, "runtime_id"))
        if self.message is not None:
            object.__setattr__(self, "message", normalize_non_empty(self.message, "message"))


@final
@dataclass(frozen=True, slots=True)
class RuntimeStatusSnapshot:
    """Read-model snapshot for public dry-run status."""

    runtime_id: str
    mode: ExecutionMode
    status: RuntimeHealth
    provider: str
    symbol: str
    last_heartbeat_at: datetime
    last_market_event_at: datetime | None = None
    current_signal: str | None = None
    simulated: bool = True

    def __post_init__(self) -> None:
        heartbeat_at = require_utc_aware(self.last_heartbeat_at)
        if heartbeat_at != self.last_heartbeat_at:
            object.__setattr__(self, "last_heartbeat_at", heartbeat_at)
        if self.last_market_event_at is not None:
            market_event_at = require_utc_aware(self.last_market_event_at)
            if market_event_at != self.last_market_event_at:
                object.__setattr__(self, "last_market_event_at", market_event_at)
        object.__setattr__(self, "runtime_id", normalize_non_empty(self.runtime_id, "runtime_id"))
        object.__setattr__(self, "provider", normalize_non_empty(self.provider, "provider"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.current_signal is not None:
            object.__setattr__(
                self,
                "current_signal",
                normalize_non_empty(self.current_signal, "current_signal"),
            )
        if not self.simulated:
            from trading_framework.core.exceptions import ValidationError

            msg = "RuntimeStatusSnapshot must be marked simulated"
            raise ValidationError(msg)
