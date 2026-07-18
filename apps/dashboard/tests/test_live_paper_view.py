"""Tests for Live Paper presentation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dashboard_app.charts.lightweight import candles_from_status_bars, markers_for_fills
from dashboard_app.views.live_paper import (
    event_timeline_rows,
    live_paper_health,
    parse_utc_datetime,
)


def test_parse_utc_datetime_accepts_z_suffix() -> None:
    parsed = parse_utc_datetime("2026-07-18T10:00:00Z")
    assert parsed == datetime(2026, 7, 18, 10, 0, tzinfo=UTC)


def test_live_paper_health_marks_stale_heartbeat() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    health = live_paper_health(
        {
            "simulated": True,
            "status": "running",
            "last_heartbeat_at": (now - timedelta(minutes=10)).isoformat(),
        },
        now=now,
        stale_after=timedelta(minutes=3),
    )
    assert health.simulated is True
    assert health.is_stale is True
    assert health.badge == "Stale"


def test_live_paper_health_fresh_heartbeat() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    health = live_paper_health(
        {
            "simulated": True,
            "status": "running",
            "last_heartbeat_at": (now - timedelta(seconds=30)).isoformat(),
        },
        now=now,
    )
    assert health.is_stale is False
    assert health.badge == "Running"


def test_live_paper_health_uses_worker_degraded_and_feed_fields() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    health = live_paper_health(
        {
            "simulated": True,
            "status": "degraded",
            "last_heartbeat_at": (now - timedelta(seconds=10)).isoformat(),
            "feed_connection_state": "reconnecting",
            "feed_reconnect_count": 2,
            "feed_last_error": "connection reset",
        },
        now=now,
    )
    assert health.badge == "Degraded"
    assert health.feed_connection_state == "reconnecting"
    assert health.feed_reconnect_count == 2
    assert health.feed_last_error == "connection reset"


def test_build_live_paper_candles_and_fill_markers() -> None:
    bars = [
        {
            "observed_at": "2026-07-18T12:00:00+00:00",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100.5,
        },
        {
            "observed_at": "2026-07-18T12:01:00+00:00",
            "open": 100.5,
            "high": 102,
            "low": 100,
            "close": 101,
        },
    ]
    candles = candles_from_status_bars(bars)
    assert len(candles) == 2
    markers = markers_for_fills(
        [{"filled_at": "2026-07-18T12:01:00+00:00", "price": 101, "side": "buy"}]
    )
    assert len(markers) == 1


def test_event_timeline_rows_normalizes_payload() -> None:
    rows = event_timeline_rows(
        [{"event_at": "t", "event_type": "heartbeat_recorded", "message": "alive"}]
    )
    assert rows[0]["event_type"] == "heartbeat_recorded"
