"""Execution event contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import final

from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.time.models.utc_instant import require_utc_aware


class ExecutionEventType(StrEnum):
    """Provider-independent execution event kinds."""

    RUNTIME_STARTED = "runtime_started"
    MARKET_EVENT_RECEIVED = "market_event_received"
    SIGNAL_GENERATED = "signal_generated"
    ORDER_INTENT_CREATED = "order_intent_created"
    SIMULATED_ORDER_FILLED = "simulated_order_filled"
    POSITION_UPDATED = "position_updated"
    HEARTBEAT_RECORDED = "heartbeat_recorded"
    RUNTIME_STOPPED = "runtime_stopped"
    RUNTIME_FAILED = "runtime_failed"


@final
@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """Immutable fact emitted by the execution runtime."""

    event_id: str
    event_type: ExecutionEventType
    occurred_at: datetime
    mode: str
    symbol: str
    payload: Mapping[str, str] | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        occurred_at = require_utc_aware(self.occurred_at)
        if occurred_at != self.occurred_at:
            object.__setattr__(self, "occurred_at", occurred_at)
        object.__setattr__(self, "event_id", normalize_non_empty(self.event_id, "event_id"))
        object.__setattr__(self, "mode", normalize_non_empty(self.mode, "mode"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.correlation_id is not None:
            object.__setattr__(
                self,
                "correlation_id",
                normalize_non_empty(self.correlation_id, "correlation_id"),
            )
        if self.payload is not None:
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
