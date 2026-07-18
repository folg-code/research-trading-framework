"""Tests for HttpAwsDryRunDataSource (GET-only status client)."""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from dashboard_app.contracts import WorkflowKind
from dashboard_app.datasources import HttpAwsDryRunDataSource


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
        HttpAwsDryRunDataSource(status_url="ftp://example.test/status")


def test_http_source_get_snapshot_and_list_sessions() -> None:
    payload = {
        "runtime_id": "btc-futures-dry-run-aws",
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

    source = HttpAwsDryRunDataSource(
        status_url="https://example.test/status",
        timeout_seconds=5.0,
        _urlopen=fake_urlopen,
    )
    snapshot = source.fetch_session_snapshot("ignored")
    assert snapshot["runtime_id"] == "btc-futures-dry-run-aws"
    assert snapshot["simulated"] is True

    sessions = source.list_live_sessions()
    assert len(sessions) == 1
    assert sessions[0].workflow is WorkflowKind.LIVE_PAPER
    assert sessions[0].run_id == "btc-futures-dry-run-aws"
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

    source = HttpAwsDryRunDataSource(
        status_url="https://example.test/status",
        _urlopen=fake_urlopen,
    )
    with pytest.raises(ValueError, match="HTTP 404"):
        source.fetch_session_snapshot("")


def test_http_source_maps_network_errors() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        del request, timeout
        raise URLError("timed out")

    source = HttpAwsDryRunDataSource(
        status_url="https://example.test/status",
        _urlopen=fake_urlopen,
    )
    with pytest.raises(ValueError, match="unreachable"):
        source.fetch_session_snapshot("")
