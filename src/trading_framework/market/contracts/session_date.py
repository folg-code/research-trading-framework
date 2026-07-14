"""Resolve CME session dates for contract trade partitioning."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import polars as pl

from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.time.models.utc_instant import require_utc_aware
from trading_framework.time.sessions import CmeEsRthSessionResolver


def trade_session_dates(
    event_times: Sequence[datetime],
    *,
    resolver: CmeEsRthSessionResolver | None = None,
) -> list[date]:
    """Resolve session dates for many timestamps in one vectorized pass."""
    if not event_times:
        return []
    session_resolver = resolver or CmeEsRthSessionResolver()
    normalized = [require_utc_aware(event_at) for event_at in event_times]
    timer = active_phase_timer()
    if timer is not None:
        with timer.phase("session.resolve_rth"):
            resolved = session_resolver.resolve(pl.Series(normalized))
        with timer.phase("session.extract_days"):
            trading_days = resolved.get_column("trading_day").to_list()
    else:
        resolved = session_resolver.resolve(pl.Series(normalized))
        trading_days = resolved.get_column("trading_day").to_list()
    return [day if isinstance(day, date) else date.fromisoformat(str(day)) for day in trading_days]


def trade_session_dates_from_ns(
    event_times_ns: Sequence[int],
    *,
    resolver: CmeEsRthSessionResolver | None = None,
) -> list[date]:
    """Resolve session dates for many nanosecond timestamps."""
    if not event_times_ns:
        return []
    session_resolver = resolver or CmeEsRthSessionResolver()
    timer = active_phase_timer()
    timestamps = pl.from_epoch(event_times_ns, time_unit="ns").dt.replace_time_zone("UTC")
    if timer is not None:
        with timer.phase("session.resolve_rth"):
            resolved = session_resolver.resolve(timestamps)
        with timer.phase("session.extract_days"):
            trading_days = resolved.get_column("trading_day").to_list()
    else:
        resolved = session_resolver.resolve(timestamps)
        trading_days = resolved.get_column("trading_day").to_list()
    return [day if isinstance(day, date) else date.fromisoformat(str(day)) for day in trading_days]


def trade_session_date(
    event_at: datetime,
    *,
    resolver: CmeEsRthSessionResolver | None = None,
) -> date:
    """Return the exchange-local trading day used for contract trade partitions."""
    return trade_session_dates([event_at], resolver=resolver)[0]
