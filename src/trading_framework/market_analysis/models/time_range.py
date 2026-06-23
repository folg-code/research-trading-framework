"""UTC time range for analysis execution."""

from dataclasses import dataclass
from datetime import datetime

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.utc_instant import require_utc_aware


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Inclusive UTC analysis range on the shared bar time axis."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = require_utc_aware(self.start)
        end = require_utc_aware(self.end)
        if end < start:
            msg = "time range end must be >= start"
            raise ValidationError(msg)
        if start != self.start:
            object.__setattr__(self, "start", start)
        if end != self.end:
            object.__setattr__(self, "end", end)

    def canonical(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"
