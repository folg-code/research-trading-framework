"""Global multi-session trading calendar resolver."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import polars as pl

from trading_framework.time.sessions.cme_es_rth import CmeEsRthSessionResolver
from trading_framework.time.sessions.constants import (
    SESSION_ASIA_COLUMN,
    SESSION_LONDON_COLUMN,
    SESSION_NEW_YORK_COLUMN,
)

_ASIA_TIMEZONE = "Asia/Tokyo"
_LONDON_TIMEZONE = "Europe/London"
_NY_TIMEZONE = "America/New_York"


def _session_membership(
    timestamps: pl.Series,
    *,
    timezone: str,
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
) -> pl.Series:
    """Weekday membership in a fixed, non-midnight-crossing local-time window."""
    local = timestamps.dt.convert_time_zone(timezone)
    weekday = local.dt.weekday()
    hour = local.dt.hour()
    minute = local.dt.minute()
    after_start = (hour > start_hour) | ((hour == start_hour) & (minute >= start_minute))
    before_end = (hour < end_hour) | ((hour == end_hour) & (minute < end_minute))
    return (weekday <= 5) & after_start & before_end


@dataclass(frozen=True, slots=True)
class GlobalSessionCalendarResolver:
    """Superset of ``CmeEsRthSessionResolver``: RTH plus named-session membership.

    Carries the same ``timestamp``/``trading_day``/``session_id``/``is_rth``
    columns as ``CmeEsRthSessionResolver`` (delegated, byte-identical RTH
    logic) plus three additional boolean columns -- ``session_asia``,
    ``session_london``, ``session_new_york`` -- one per named intraday
    session, each a fixed, documented, non-midnight-crossing local-time
    window on weekdays only:

    - Asia: 00:00-09:00 ``Asia/Tokyo``
    - London: 08:00-16:30 ``Europe/London``
    - New York: 09:30-16:00 ``America/New_York``

    New York's window happens to match CME ES RTH's own hours, but is
    computed and stored separately (``session_new_york`` vs ``is_rth``) --
    the two answer different questions ("is this bar in the NY trading
    session" vs. "is this bar in CME ES RTH") and this resolver does not
    assume one implies the other for a future instrument or session
    definition where they might diverge.

    Per ADR-MA-015: additive, not a replacement for
    ``CmeEsRthSessionResolver`` -- existing callers that only need RTH are
    unaffected and may keep using the plain resolver.
    """

    holiday_dates: frozenset[date] | None = None

    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        rth_frame = CmeEsRthSessionResolver(holiday_dates=self.holiday_dates).resolve(timestamps)
        asia = _session_membership(
            timestamps,
            timezone=_ASIA_TIMEZONE,
            start_hour=0,
            start_minute=0,
            end_hour=9,
            end_minute=0,
        )
        london = _session_membership(
            timestamps,
            timezone=_LONDON_TIMEZONE,
            start_hour=8,
            start_minute=0,
            end_hour=16,
            end_minute=30,
        )
        new_york = _session_membership(
            timestamps,
            timezone=_NY_TIMEZONE,
            start_hour=9,
            start_minute=30,
            end_hour=16,
            end_minute=0,
        )
        return rth_frame.with_columns(
            asia.alias(SESSION_ASIA_COLUMN),
            london.alias(SESSION_LONDON_COLUMN),
            new_york.alias(SESSION_NEW_YORK_COLUMN),
        )


__all__ = ["GlobalSessionCalendarResolver"]
