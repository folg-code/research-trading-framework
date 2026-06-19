"""Clock protocol for time-dependent logic."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provide the current UTC-aware time."""

    def now(self) -> datetime:
        """Return the current time as a UTC-aware datetime."""
        ...
