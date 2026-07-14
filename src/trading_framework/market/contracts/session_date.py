"""Resolve CME session dates for contract trade partitioning."""

from __future__ import annotations

from datetime import date, datetime

import polars as pl

from trading_framework.time.models.utc_instant import require_utc_aware
from trading_framework.time.sessions import CmeEsRthSessionResolver


def trade_session_date(
    event_at: datetime,
    *,
    resolver: CmeEsRthSessionResolver | None = None,
) -> date:
    """Return the exchange-local trading day used for contract trade partitions."""
    event = require_utc_aware(event_at)
    session_resolver = resolver or CmeEsRthSessionResolver()
    resolved = session_resolver.resolve(pl.Series([event]))
    trading_day: date = resolved.row(0, named=True)["trading_day"]
    return trading_day
