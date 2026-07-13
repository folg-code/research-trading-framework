"""Bar timeframe value object."""

import re
from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError

_TIMEFRAME_PATTERN = re.compile(r"^(\d+)([mhd])$")
_UNIT_TO_SECONDS = {"m": 60, "h": 3600, "d": 86400}
_EVENT_LEVEL_TIMEFRAME = "tick"


@dataclass(frozen=True, slots=True)
class Timeframe:
    """Immutable bar duration or event-level ``tick`` identity."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if normalized == _EVENT_LEVEL_TIMEFRAME:
            if normalized != self.value:
                object.__setattr__(self, "value", normalized)
            return
        if not _TIMEFRAME_PATTERN.fullmatch(normalized):
            msg = f"invalid timeframe: {self.value!r}"
            raise ValidationError(msg)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    @property
    def is_event_level(self) -> bool:
        """Return whether the timeframe denotes event-level facts rather than bars."""
        return self.value == _EVENT_LEVEL_TIMEFRAME

    @property
    def total_seconds(self) -> int:
        """Return the duration in seconds."""
        if self.is_event_level:
            msg = "event-level timeframe tick has no bar duration"
            raise ValidationError(msg)
        match = _TIMEFRAME_PATTERN.fullmatch(self.value)
        if match is None:
            msg = f"invalid timeframe: {self.value!r}"
            raise ValidationError(msg)
        amount = int(match.group(1))
        unit = match.group(2)
        return amount * _UNIT_TO_SECONDS[unit]

    def __str__(self) -> str:
        return self.value
