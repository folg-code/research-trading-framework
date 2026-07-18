"""Derive RuntimeHealth from market-feed freshness (separate from process liveness)."""

from __future__ import annotations

from datetime import datetime, timedelta

from trading_framework.execution.models.market_data import MarketFeedConnectionState
from trading_framework.execution.models.status import RuntimeHealth
from trading_framework.time.models.utc_instant import require_utc_aware

DEFAULT_DEGRADED_AFTER = timedelta(seconds=90)
DEFAULT_STALE_AFTER = timedelta(seconds=180)


def resolve_runtime_health(
    *,
    now: datetime,
    last_market_event_at: datetime | None,
    feed_connection: MarketFeedConnectionState | None = None,
    degraded_after: timedelta = DEFAULT_DEGRADED_AFTER,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
) -> RuntimeHealth:
    """Map feed freshness / connection state to public runtime health.

    Process liveness is implied by the caller still emitting heartbeats. This
    function only answers whether the **market feed** looks healthy.
    """
    if degraded_after <= timedelta(0):
        msg = "degraded_after must be positive"
        raise ValueError(msg)
    if stale_after < degraded_after:
        msg = "stale_after must be >= degraded_after"
        raise ValueError(msg)

    clock = require_utc_aware(now)
    if feed_connection is MarketFeedConnectionState.RECONNECTING:
        return RuntimeHealth.DEGRADED
    if feed_connection is MarketFeedConnectionState.FAILED:
        return RuntimeHealth.DEGRADED

    if last_market_event_at is None:
        # Startup / no bars yet: keep RUNNING unless the feed itself is bad.
        return RuntimeHealth.RUNNING

    event_at = require_utc_aware(last_market_event_at)
    age = clock - event_at
    if age >= stale_after:
        return RuntimeHealth.STALE
    if age >= degraded_after:
        return RuntimeHealth.DEGRADED
    return RuntimeHealth.RUNNING
