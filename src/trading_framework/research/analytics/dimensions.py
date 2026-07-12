"""Analytics grouping dimensions and timestamp basis."""

from __future__ import annotations

from enum import StrEnum

ENTITY_KIND_SIGNAL = "SIGNAL_OCCURRENCE"
ENTITY_KIND_OBSERVATION = "MARKET_MODEL_OBSERVATION"


class AnalyticsTimestampBasis(StrEnum):
    """Timestamp column used for time-derived grouping dimensions."""

    AVAILABLE_AT = "available_at"
    DETECTED_AT = "detected_at"


class GroupDimension(StrEnum):
    """Fixed MVP grouping dimensions — not a dynamic dimension framework."""

    HORIZON = "horizon"
    RTH_MEMBERSHIP = "rth_membership"
    TIME_OF_DAY = "time_of_day"
    CALENDAR_MONTH = "calendar_month"
    CONTEXT_MET = "context_met"
