"""Tests for feed-freshness RuntimeHealth policy."""

from datetime import UTC, datetime, timedelta

import pytest

from trading_framework.execution import MarketFeedConnectionState, RuntimeHealth
from trading_framework.execution.runtime.health_policy import resolve_runtime_health

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def test_resolve_runtime_health_running_when_feed_fresh() -> None:
    health = resolve_runtime_health(
        now=NOW,
        last_market_event_at=NOW - timedelta(seconds=10),
        feed_connection=MarketFeedConnectionState.CONNECTED,
        degraded_after=timedelta(seconds=90),
        stale_after=timedelta(seconds=180),
    )
    assert health is RuntimeHealth.RUNNING


def test_resolve_runtime_health_degraded_on_reconnect_or_age() -> None:
    reconnecting = resolve_runtime_health(
        now=NOW,
        last_market_event_at=NOW - timedelta(seconds=5),
        feed_connection=MarketFeedConnectionState.RECONNECTING,
    )
    aged = resolve_runtime_health(
        now=NOW,
        last_market_event_at=NOW - timedelta(seconds=100),
        feed_connection=MarketFeedConnectionState.CONNECTED,
        degraded_after=timedelta(seconds=90),
        stale_after=timedelta(seconds=180),
    )
    assert reconnecting is RuntimeHealth.DEGRADED
    assert aged is RuntimeHealth.DEGRADED


def test_resolve_runtime_health_stale_when_market_event_too_old() -> None:
    health = resolve_runtime_health(
        now=NOW,
        last_market_event_at=NOW - timedelta(seconds=200),
        feed_connection=MarketFeedConnectionState.CONNECTED,
        degraded_after=timedelta(seconds=90),
        stale_after=timedelta(seconds=180),
    )
    assert health is RuntimeHealth.STALE


def test_resolve_runtime_health_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="stale_after"):
        resolve_runtime_health(
            now=NOW,
            last_market_event_at=NOW,
            degraded_after=timedelta(seconds=120),
            stale_after=timedelta(seconds=60),
        )
