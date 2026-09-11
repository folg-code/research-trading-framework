"""Tests for the VPS dry-run status service: aiohttp wiring and end-to-end sanitization."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from scripts.execution import run_vps_status_service

from trading_framework.application.execution import load_vps_execution_status_api_config
from trading_framework.application.execution.vps_status_api import SCHEMA_VERSION
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def _write_raw_state(
    base_path: Path, runtime_id: str, extra_status_fields: dict[str, object]
) -> None:
    """Write a raw state.json document with fields outside the typed read model."""
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
            "last_heartbeat_at": NOW.isoformat(),
            "last_market_event_at": NOW.isoformat(),
            "current_signal": None,
            "feed_connection_state": "connected",
            "feed_reconnect_count": 0,
            "feed_last_error": None,
            "simulated": True,
            **extra_status_fields,
        },
        "events": [],
        "orders": [],
        "fills": [],
        "bars": [],
        "position": None,
        "account": None,
        # Top-level unexpected field injected directly into the persisted document.
        "state_file_path": str(runtime_dir / "state.json"),
        "container_host": "dry-run-worker-7f9c",
    }
    (runtime_dir / "state.json").write_text(json.dumps(document), encoding="utf-8")


def _request(
    app: web.Application, path: str, method: str = "GET"
) -> tuple[int, dict[str, str], bytes]:
    async def run() -> tuple[int, dict[str, str], bytes]:
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.request(method, path)
            body = await response.read()
            return response.status, dict(response.headers), body
        finally:
            await client.close()

    return asyncio.run(run())


def _config(tmp_path: Path, runtime_id: str) -> Any:
    return run_vps_status_service.ServiceRuntimeConfig(
        host="127.0.0.1",
        port=0,
        api_config=load_vps_execution_status_api_config(
            {"TRADING_FRAMEWORK_STATUS_RUNTIME_ID": runtime_id}
        ),
        state_repository=JsonExecutionStateRepository(tmp_path),
    )


def test_status_endpoint_never_emits_unexpected_persisted_fields(tmp_path: Path) -> None:
    _write_raw_state(
        tmp_path,
        "vps-runtime-1",
        {
            "unexpected_secret_field": "sk-not-a-real-secret",
            "internal_debug_path": "/var/lib/execution-state",
        },
    )
    app = run_vps_status_service.create_app(_config(tmp_path, "vps-runtime-1"))

    status, headers, raw_body = _request(app, "/status")
    body = json.loads(raw_body)

    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cache-Control"] == "no-store"
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["simulated"] is True
    assert "unexpected_secret_field" not in body
    assert "internal_debug_path" not in body
    assert "state_file_path" not in body
    assert "container_host" not in body
    assert str(tmp_path) not in json.dumps(body)
    assert "sk-not-a-real-secret" not in json.dumps(body)


def test_status_endpoint_returns_404_for_missing_runtime(tmp_path: Path) -> None:
    app = run_vps_status_service.create_app(_config(tmp_path, "missing-runtime"))

    status, _headers, raw_body = _request(app, "/status")
    body = json.loads(raw_body)

    assert status == 404
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["simulated"] is True


def test_status_endpoint_rejects_post_with_405_and_allow_header(tmp_path: Path) -> None:
    _write_raw_state(tmp_path, "vps-runtime-1", {})
    app = run_vps_status_service.create_app(_config(tmp_path, "vps-runtime-1"))

    status, headers, raw_body = _request(app, "/status", method="POST")
    body = json.loads(raw_body)

    assert status == 405
    assert headers["Allow"] == "GET"
    assert body["schema_version"] == SCHEMA_VERSION


def test_health_endpoint_is_healthy_with_no_state_at_all(tmp_path: Path) -> None:
    app = run_vps_status_service.create_app(_config(tmp_path, "no-such-runtime"))

    status, _headers, raw_body = _request(app, "/healthz")
    body = json.loads(raw_body)

    assert status == 200
    assert body["status"] == "ok"
    assert body["state_volume_readable"] is True


def test_status_endpoint_returns_503_for_corrupt_state(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "vps-runtime-1"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "state.json").write_text('{"version": 999}', encoding="utf-8")
    app = run_vps_status_service.create_app(_config(tmp_path, "vps-runtime-1"))

    status, _headers, raw_body = _request(app, "/status")
    body = json.loads(raw_body)

    assert status == 503
    assert body["error"] == "status_unavailable"
    assert body["schema_version"] == SCHEMA_VERSION


def test_status_endpoint_supports_head_request(tmp_path: Path) -> None:
    """The wildcard ``/status`` route must still honor HEAD, not only GET, at the real
    aiohttp transport layer (the pure handler is covered separately in
    ``test_vps_status_api.py``, but wiring could still break HEAD end-to-end)."""
    _write_raw_state(tmp_path, "vps-runtime-1", {})
    app = run_vps_status_service.create_app(_config(tmp_path, "vps-runtime-1"))

    status, headers, _raw_body = _request(app, "/status", method="HEAD")

    assert status == 200
    assert headers["Cache-Control"] == "no-store"


def test_status_endpoint_sets_no_cors_headers(tmp_path: Path) -> None:
    """ADR-0036 section 3.7: no CORS wildcard is needed or set; the only caller is
    server-side on the private network."""
    _write_raw_state(tmp_path, "vps-runtime-1", {})
    app = run_vps_status_service.create_app(_config(tmp_path, "vps-runtime-1"))

    _status, headers, _raw_body = _request(app, "/status")

    assert not any(name.lower().startswith("access-control") for name in headers)
    assert "origin" not in {name.lower() for name in headers}


def test_load_service_runtime_config_requires_state_path() -> None:
    with pytest.raises(ConfigurationError):
        run_vps_status_service.load_service_runtime_config({})


def test_load_service_runtime_config_rejects_invalid_port(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        run_vps_status_service.load_service_runtime_config(
            {
                "TRADING_FRAMEWORK_STATUS_STATE_PATH": str(tmp_path),
                "TRADING_FRAMEWORK_STATUS_PORT": "not-a-port",
            }
        )


def test_main_returns_1_and_prints_error_when_state_path_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("TRADING_FRAMEWORK_STATUS_STATE_PATH", raising=False)

    exit_code = run_vps_status_service.main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "TRADING_FRAMEWORK_STATUS_STATE_PATH" in captured.err


def test_load_service_runtime_config_from_env(tmp_path: Path) -> None:
    config = run_vps_status_service.load_service_runtime_config(
        {
            "TRADING_FRAMEWORK_STATUS_STATE_PATH": str(tmp_path),
            "TRADING_FRAMEWORK_STATUS_HOST": "127.0.0.1",
            "TRADING_FRAMEWORK_STATUS_PORT": "9091",
            "TRADING_FRAMEWORK_STATUS_RUNTIME_ID": "vps-runtime-1",
        }
    )

    assert config.host == "127.0.0.1"
    assert config.port == 9091
    assert config.api_config.runtime_id == "vps-runtime-1"
