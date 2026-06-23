"""Market bar model."""

from dataclasses import dataclass
from datetime import datetime
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.time.models.utc_instant import require_utc_aware


@final
@dataclass(frozen=True, slots=True)
class MarketBar:
    """Immutable OHLCV bar with canonical UTC interval boundaries."""

    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume
    observed_at: datetime
    available_at: datetime

    def __post_init__(self) -> None:
        observed = require_utc_aware(self.observed_at)
        available = require_utc_aware(self.available_at)
        if observed != self.observed_at:
            object.__setattr__(self, "observed_at", observed)
        if available != self.available_at:
            object.__setattr__(self, "available_at", available)
        if self.available_at <= self.observed_at:
            msg = "available_at must be after observed_at"
            raise ValidationError(msg)

        open_value = self.open.value
        high_value = self.high.value
        low_value = self.low.value
        close_value = self.close.value

        if high_value < open_value or high_value < close_value:
            msg = "high must be >= open and close"
            raise ValidationError(msg)
        if low_value > open_value or low_value > close_value:
            msg = "low must be <= open and close"
            raise ValidationError(msg)
        if high_value < low_value:
            msg = "high must be >= low"
            raise ValidationError(msg)
