"""Metadata captured alongside ephemeral analytics results."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter

CME_ES_TIME_OF_DAY_TIMEZONE = "America/New_York"
DEFAULT_TIME_OF_DAY_BUCKET_MINUTES = 60


@dataclass(frozen=True, slots=True)
class AnalyticsResultMetadata:
    """Records analytical choices applied to one run interpretation."""

    source_run_id: str
    research_scope: str
    timestamp_basis: AnalyticsTimestampBasis
    outcome_filter: OutcomeAnalyticsFilter
    time_of_day_timezone: str = CME_ES_TIME_OF_DAY_TIMEZONE
    time_of_day_bucket_minutes: int = DEFAULT_TIME_OF_DAY_BUCKET_MINUTES
