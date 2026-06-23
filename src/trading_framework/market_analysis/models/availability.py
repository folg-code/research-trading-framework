"""Availability metadata for analysis outputs."""

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError


class AvailabilityPolicy(StrEnum):
    """When a computed value becomes available relative to observation time."""

    SAME_BAR = "same_bar"
    DELAYED_BARS = "delayed_bars"
    RETROSPECTIVE = "retrospective"


@dataclass(frozen=True, slots=True)
class AvailabilityMetadata:
    """Availability semantics for one analysis result."""

    policy: AvailabilityPolicy
    delay_bars: int = 0

    def __post_init__(self) -> None:
        if self.delay_bars < 0:
            msg = "delay_bars must be >= 0"
            raise ValidationError(msg)
        if self.policy is AvailabilityPolicy.DELAYED_BARS and self.delay_bars < 1:
            msg = "delayed_bars policy requires delay_bars >= 1"
            raise ValidationError(msg)
        if self.policy is not AvailabilityPolicy.DELAYED_BARS and self.delay_bars != 0:
            msg = "delay_bars must be 0 unless policy is delayed_bars"
            raise ValidationError(msg)
