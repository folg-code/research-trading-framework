"""Market trade model."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.time.models.utc_instant import require_utc_aware


class TradeSide(StrEnum):
    """Normalized aggressor side for a market trade."""

    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


@final
@dataclass(frozen=True, slots=True)
class MarketTrade:
    """Immutable single trade event with canonical UTC timestamps."""

    price: Price
    size: Volume
    event_at: datetime
    side: TradeSide
    received_at: datetime | None = None
    trade_id: str | None = None
    sequence: int | None = None

    def __post_init__(self) -> None:
        event = require_utc_aware(self.event_at)
        if event != self.event_at:
            object.__setattr__(self, "event_at", event)

        if self.received_at is not None:
            received = require_utc_aware(self.received_at)
            if received != self.received_at:
                object.__setattr__(self, "received_at", received)
            if self.received_at < self.event_at:
                msg = "received_at must not be before event_at"
                raise ValidationError(msg)

        if self.size.value <= 0:
            msg = "trade size must be positive"
            raise ValidationError(msg)

        if self.sequence is not None and self.sequence < 0:
            msg = "sequence must be non-negative when present"
            raise ValidationError(msg)
