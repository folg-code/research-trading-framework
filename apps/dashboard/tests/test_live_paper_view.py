"""Tests for Live Paper presentation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dashboard_app.charts.lightweight import candles_from_status_bars, markers_for_fills
from dashboard_app.views.live_paper import (
    build_dry_run_status_card,
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


def test_dry_run_status_card_not_configured_without_a_status_url() -> None:
    card = build_dry_run_status_card(status_url=None, snapshot=None, error=None)
    assert card.kind == "not_configured"
    assert card.snapshot is None
    assert card.health is None

    card = build_dry_run_status_card(status_url="  ", snapshot=None, error=None)
    assert card.kind == "not_configured"


def test_dry_run_status_card_current_for_a_fresh_running_snapshot() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "status": "RUNNING",
        "stale": False,
        "last_heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "current"
    assert card.snapshot == snapshot
    assert card.health is not None
    assert card.health.is_stale is False


def test_dry_run_status_card_stale_when_response_marks_stale_true() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "status": "RUNNING",
        "stale": True,
        "last_heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "stale"
    assert card.snapshot == snapshot


def test_dry_run_status_card_stale_from_old_heartbeat_even_without_stale_flag() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "status": "RUNNING",
        "last_heartbeat_at": (now - timedelta(minutes=10)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "stale"


def test_dry_run_status_card_failed_status_is_reported_as_failed_not_current() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "status": "FAILED",
        "stale": False,
        "last_heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "failed"
    assert card.snapshot == snapshot


def test_dry_run_status_card_offline_when_status_api_is_unreachable() -> None:
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status",
        snapshot=None,
        error="status API unreachable: [Errno 111] Connection refused",
    )
    assert card.kind == "offline"
    assert card.snapshot is None


def test_dry_run_status_card_not_found_on_http_404() -> None:
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status",
        snapshot=None,
        error="status API HTTP 404: {}",
    )
    assert card.kind == "not_found"


def test_dry_run_status_card_unavailable_on_other_http_errors() -> None:
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status",
        snapshot=None,
        error="status API HTTP 503: {}",
    )
    assert card.kind == "unavailable"


def test_dry_run_status_card_unavailable_when_status_field_is_missing() -> None:
    """A snapshot missing `status` entirely must never be classified as
    ``current`` -- ADR-0035 SS3.2's closed vocabulary is a required field, and
    its absence signals an untrustworthy/malformed response, not a healthy one."""
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "stale": False,
        "last_heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "unavailable"
    assert card.health is None


def test_dry_run_status_card_unavailable_when_status_field_is_unrecognized() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    snapshot = {
        "status": "banana",
        "last_heartbeat_at": (now - timedelta(seconds=5)).isoformat(),
        "symbol": "BTCUSDT",
    }
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status", snapshot=snapshot, error=None, now=now
    )
    assert card.kind == "unavailable"


def test_dry_run_status_card_never_presents_a_prior_snapshot_as_current_on_error() -> None:
    """Callers pass only the current call's snapshot; an error always wins over
    any stale value a caller might mistakenly still be holding."""
    card = build_dry_run_status_card(
        status_url="http://dry-run-status:8090/status",
        snapshot=None,
        error="status API unreachable: timed out",
    )
    assert card.kind == "offline"
    assert card.snapshot is None
    assert card.health is None
