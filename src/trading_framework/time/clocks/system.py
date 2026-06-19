"""System clock implementation."""

from datetime import UTC, datetime
from typing import final


@final
class SystemClock:
    """Return the current system time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
