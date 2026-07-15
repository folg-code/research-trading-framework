"""Live market data contracts used by execution runtimes."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.time.models.utc_instant import require_utc_aware


class MarketFeedConnectionState(StrEnum):
    """Provider-independent live market feed connection state."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"
    FAILED = "failed"


@final
@dataclass(frozen=True, slots=True)
class BestBidAskSnapshot:
    """Best bid/ask snapshot for simulated fill references."""

    symbol: str
    bid_price: Price
    ask_price: Price
    event_at: datetime
    received_at: datetime | None = None

    def __post_init__(self) -> None:
        event_at = require_utc_aware(self.event_at)
        if event_at != self.event_at:
            object.__setattr__(self, "event_at", event_at)
        if self.received_at is not None:
            received_at = require_utc_aware(self.received_at)
            if received_at != self.received_at:
                object.__setattr__(self, "received_at", received_at)
            if self.received_at < self.event_at:
                msg = "received_at must not be before event_at"
                raise ValidationError(msg)
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.bid_price.value > self.ask_price.value:
            msg = "bid_price must be <= ask_price"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class MarketFeedStatusSnapshot:
    """Read-model snapshot for a live market data feed."""

    provider: str
    symbol: str
    state: MarketFeedConnectionState
    recorded_at: datetime
    last_message_at: datetime | None = None
    reconnect_count: int = 0
    last_error: str | None = None

    def __post_init__(self) -> None:
        recorded_at = require_utc_aware(self.recorded_at)
        if recorded_at != self.recorded_at:
            object.__setattr__(self, "recorded_at", recorded_at)
        if self.last_message_at is not None:
            last_message_at = require_utc_aware(self.last_message_at)
            if last_message_at != self.last_message_at:
                object.__setattr__(self, "last_message_at", last_message_at)
            if self.last_message_at > self.recorded_at:
                msg = "last_message_at must not be after recorded_at"
                raise ValidationError(msg)
        if self.reconnect_count < 0:
            msg = "reconnect_count must be non-negative"
            raise ValidationError(msg)
        object.__setattr__(self, "provider", normalize_non_empty(self.provider, "provider"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.last_error is not None:
            object.__setattr__(
                self,
                "last_error",
                normalize_non_empty(self.last_error, "last_error"),
            )
