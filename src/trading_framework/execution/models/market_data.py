"""Live market data contracts used by execution runtimes."""

from dataclasses import dataclass
from datetime import datetime
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.time.models.utc_instant import require_utc_aware


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
