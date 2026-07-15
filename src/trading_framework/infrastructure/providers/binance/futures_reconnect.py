"""Reconnect backoff policy for Binance USD-M futures feeds."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.models._validation import normalize_positive_decimal


@final
@dataclass(frozen=True, slots=True)
class ReconnectBackoffPolicy:
    """Bounded exponential reconnect backoff policy."""

    initial_delay: timedelta = timedelta(seconds=1)
    max_delay: timedelta = timedelta(seconds=30)
    multiplier: Decimal = Decimal("2")
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.initial_delay <= timedelta(0):
            msg = "initial_delay must be positive"
            raise ValidationError(msg)
        if self.max_delay < self.initial_delay:
            msg = "max_delay must be >= initial_delay"
            raise ValidationError(msg)
        multiplier = normalize_positive_decimal(self.multiplier, "multiplier")
        if multiplier < Decimal("1"):
            msg = "multiplier must be >= 1"
            raise ValidationError(msg)
        object.__setattr__(self, "multiplier", multiplier)
        if self.max_attempts < 1:
            msg = "max_attempts must be positive"
            raise ValidationError(msg)

    def delay_for_attempt(self, attempt_index: int) -> timedelta:
        """Return a capped delay for a zero-based reconnect attempt."""
        if attempt_index < 0:
            msg = "attempt_index must be non-negative"
            raise ValidationError(msg)
        if attempt_index >= self.max_attempts:
            msg = "attempt_index exceeds max_attempts"
            raise ValidationError(msg)

        initial_seconds = Decimal(str(self.initial_delay.total_seconds()))
        max_seconds = Decimal(str(self.max_delay.total_seconds()))
        delay_seconds = initial_seconds * (self.multiplier**attempt_index)
        capped_seconds = min(delay_seconds, max_seconds)
        return timedelta(seconds=float(capped_seconds))


DEFAULT_RECONNECT_BACKOFF_POLICY = ReconnectBackoffPolicy()
