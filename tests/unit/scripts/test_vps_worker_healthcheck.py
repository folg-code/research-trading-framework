"""Tests for the VPS worker's in-container liveness health check."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts.execution import vps_worker_healthcheck

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def _write_raw_state(base_path: Path, runtime_id: str, last_heartbeat_at: datetime) -> None:
    runtime_dir = base_path / runtime_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "version": 1,
        "status": {
            "runtime_id": runtime_id,
            "mode": "dry_run",
            "status": "running",
            "provider": "binance_usdm",
            "symbol": "BTCUSDT",
            "last_heartbeat_at": last_heartbeat_at.isoformat(),
            "last_market_event_at": last_heartbeat_at.isoformat(),
            "current_signal": None,
            "feed_connection_state": "connected",
            "feed_reconnect_count": 0,
            "feed_last_error": None,
            "simulated": True,
        },
        "events": [],
        "orders": [],
        "fills": [],
        "bars": [],
        "position": None,
        "account": None,
    }
    (runtime_dir / "state.json").write_text(json.dumps(document), encoding="utf-8")


def test_healthy_with_no_state_at_all_startup_grace_period(tmp_path: Path) -> None:
    env = {
        "TRADING_FRAMEWORK_VPS_STATE_PATH": str(tmp_path),
        "TRADING_FRAMEWORK_VPS_RUNTIME_ID": "vps-runtime-1",
    }

    assert vps_worker_healthcheck.check_worker_is_healthy(env, now=NOW) is True


def test_healthy_when_heartbeat_is_fresh(tmp_path: Path) -> None:
    _write_raw_state(tmp_path, "vps-runtime-1", NOW - timedelta(seconds=30))
    env = {
        "TRADING_FRAMEWORK_VPS_STATE_PATH": str(tmp_path),
        "TRADING_FRAMEWORK_VPS_RUNTIME_ID": "vps-runtime-1",
    }

    assert vps_worker_healthcheck.check_worker_is_healthy(env, now=NOW) is True


def test_unhealthy_when_heartbeat_is_stale(tmp_path: Path) -> None:
    _write_raw_state(tmp_path, "vps-runtime-1", NOW - timedelta(seconds=999))
    env = {
        "TRADING_FRAMEWORK_VPS_STATE_PATH": str(tmp_path),
        "TRADING_FRAMEWORK_VPS_RUNTIME_ID": "vps-runtime-1",
        "TRADING_FRAMEWORK_VPS_HEALTHCHECK_STALE_AFTER_SECONDS": "120",
    }

    assert vps_worker_healthcheck.check_worker_is_healthy(env, now=NOW) is False


def test_unhealthy_when_state_is_corrupt(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "vps-runtime-1"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "state.json").write_text('{"version": 999}', encoding="utf-8")
    env = {
        "TRADING_FRAMEWORK_VPS_STATE_PATH": str(tmp_path),
        "TRADING_FRAMEWORK_VPS_RUNTIME_ID": "vps-runtime-1",
    }

    assert vps_worker_healthcheck.check_worker_is_healthy(env, now=NOW) is False


def test_main_returns_0_when_healthy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_raw_state(tmp_path, "vps-runtime-1", datetime.now(UTC))
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_STATE_PATH", str(tmp_path))
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_RUNTIME_ID", "vps-runtime-1")

    assert vps_worker_healthcheck.main() == 0


def test_main_returns_1_when_stale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_raw_state(tmp_path, "vps-runtime-1", datetime(2000, 1, 1, tzinfo=UTC))
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_STATE_PATH", str(tmp_path))
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_RUNTIME_ID", "vps-runtime-1")

    assert vps_worker_healthcheck.main() == 1


def test_main_returns_1_on_invalid_threshold_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_STATE_PATH", str(tmp_path))
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_HEALTHCHECK_STALE_AFTER_SECONDS", "not-a-number")

    assert vps_worker_healthcheck.main() == 1
