"""Tests for HttpLivePaperStatusDataSource (GET-only status client)."""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from dashboard_app.contracts import WorkflowKind
from dashboard_app.datasources import HttpLivePaperStatusDataSource


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], *, status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_http_source_rejects_non_http_url() -> None:
    with pytest.raises(ValueError, match="http"):
        HttpLivePaperStatusDataSource(status_url="ftp://example.test/status")


def test_http_source_get_snapshot_and_list_sessions() -> None:
    payload = {
        "runtime_id": "btc-futures-dry-run-vps",
        "symbol": "BTCUSDT",
        "status": "running",
        "mode": "dry_run",
        "last_heartbeat_at": "2026-07-18T10:00:00+00:00",
        "paper_equity": 10000.0,
        "simulated": True,
    }
    calls: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        calls.append(request)
        assert timeout == 5.0
        assert request.get_method() == "GET"
        assert request.full_url == "https://example.test/status"
        return _FakeResponse(payload)

    source = HttpLivePaperStatusDataSource(
        status_url="https://example.test/status",
        timeout_seconds=5.0,
        _urlopen=fake_urlopen,
    )
    snapshot = source.fetch_session_snapshot("ignored")
    assert snapshot["runtime_id"] == "btc-futures-dry-run-vps"
    assert snapshot["simulated"] is True

    sessions = source.list_live_sessions()
    assert len(sessions) == 1
    assert sessions[0].workflow is WorkflowKind.LIVE_PAPER
    assert sessions[0].run_id == "btc-futures-dry-run-vps"
    assert "BTCUSDT" in sessions[0].title
    assert len(calls) == 2


def test_http_source_maps_http_errors() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        del request, timeout
        raise HTTPError(
            "https://example.test/status",
            404,
            "Not Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"error":"runtime_status_not_found"}'),
        )

    source = HttpLivePaperStatusDataSource(
        status_url="https://example.test/status",
        _urlopen=fake_urlopen,
    )
    with pytest.raises(ValueError, match="HTTP 404"):
        source.fetch_session_snapshot("")


def test_http_source_parses_vps_status_v1_response_unchanged() -> None:
    """Regression: the VPS status service's execution.status.v1 shape (ADR-0035 section 3)
    parses through this datasource without any code change, since it is a superset of the
    fields this client already reads."""
    payload = {
        "schema_version": "execution.status.v1",
        "generated_at": "2026-07-18T10:00:05+00:00",
        "simulated": True,
        "runtime_id": "btc-futures-dry-run-vps",
        "mode": "dry_run",
        "provider": "binance_usdm",
        "symbol": "BTCUSDT",
        "status": "running",
        "last_heartbeat_at": "2026-07-18T10:00:00+00:00",
        "last_market_event_at": "2026-07-18T09:59:55+00:00",
        "feed_connection_state": "connected",
        "feed_reconnect_count": 0,
        "feed_last_error_code": None,
        "stale": False,
        "last_price": "65010",
        "recent_bars": [],
        "paper_equity": "10010",
        "realized_pnl": "0",
        "unrealized_pnl": "10",
        "current_position": {
            "symbol": "BTCUSDT",
            "side": "long",
            "quantity": "0.001",
            "average_entry_price": "65000",
            "mark_price": "65010",
            "unrealized_pnl": "10",
            "updated_at": "2026-07-18T10:00:00+00:00",
            "simulated": True,
        },
        "current_signal": "entry_signal_active",
        "recent_orders": [],
        "recent_fills": [],
        "recent_events": [],
    }

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        del request, timeout
        return _FakeResponse(payload)

    source = HttpLivePaperStatusDataSource(
        status_url="http://dry-run-status:8090/status",
        _urlopen=fake_urlopen,
    )
    snapshot = source.fetch_session_snapshot("ignored")
    assert snapshot == payload

    sessions = source.list_live_sessions()
    assert len(sessions) == 1
    assert sessions[0].run_id == "btc-futures-dry-run-vps"
    assert sessions[0].workflow is WorkflowKind.LIVE_PAPER
    assert "BTCUSDT" in sessions[0].title
    assert "running" in sessions[0].title


def test_http_source_maps_network_errors() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        del request, timeout
        raise URLError("timed out")

    source = HttpLivePaperStatusDataSource(
        status_url="https://example.test/status",
        _urlopen=fake_urlopen,
    )
    with pytest.raises(ValueError, match="unreachable"):
        source.fetch_session_snapshot("")
