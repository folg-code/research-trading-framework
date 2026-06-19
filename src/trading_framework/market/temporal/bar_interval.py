"""Bar interval timestamp helpers."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.models.utc_instant import require_utc_aware


class BarTimestampSemantics(StrEnum):
    """Provider timestamp semantics supported by the MVP normalizer."""

    INTERVAL_START = "interval_start"
    INTERVAL_END = "interval_end"


def derive_bar_interval(
    observed_at: datetime,
    timeframe: Timeframe,
) -> tuple[datetime, datetime]:
    """Derive canonical ``(observed_at, available_at)`` from interval start."""
    interval_start = require_utc_aware(observed_at).astimezone(UTC)
    interval_end = interval_start + timedelta(seconds=timeframe.total_seconds)
    return interval_start, require_utc_aware(interval_end)


def normalize_provider_bar_timestamp(
    timestamp: datetime,
    *,
    timeframe: Timeframe,
    semantics: BarTimestampSemantics,
) -> tuple[datetime, datetime]:
    """Normalize a provider timestamp to canonical bar interval boundaries."""
    aware = require_utc_aware(timestamp).astimezone(UTC)
    match semantics:
        case BarTimestampSemantics.INTERVAL_START:
            return derive_bar_interval(aware, timeframe)
        case BarTimestampSemantics.INTERVAL_END:
            interval_start = aware - timedelta(seconds=timeframe.total_seconds)
            return derive_bar_interval(interval_start, timeframe)
