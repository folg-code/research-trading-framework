"""Fixed clock for deterministic tests."""

from datetime import datetime
from typing import final

from trading_framework.time.models.utc_instant import require_utc_aware


@final
class FixedClock:
    """Return a fixed UTC-aware timestamp."""

    def __init__(self, fixed_time: datetime) -> None:
        self._fixed_time = require_utc_aware(fixed_time)

    def now(self) -> datetime:
        return self._fixed_time
