"""Tests for VPS BTC futures dry-run runtime configuration."""

import asyncio
import signal
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from trading_framework.application.execution.vps_btc_futures_runtime import (
    VpsBtcFuturesRuntimeConfig,
    create_vps_execution_state_repository,
    load_vps_btc_futures_runtime_config,
    run_vps_btc_futures_dry_run,
)
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository


def test_load_vps_btc_futures_runtime_config_requires_no_aws_value() -> None:
    """No AWS_REGION/EXECUTION_STATE_TABLE is required to build a valid config (D062-02)."""
    config = load_vps_btc_futures_runtime_config({})

    assert config.runtime_id == "btc-futures-dry-run-vps"
    assert config.symbol == "BTCUSDT"
    assert config.duration_seconds is None
    assert config.is_continuous is True


def test_load_vps_btc_futures_runtime_config_defaults_to_dedicated_volume_path() -> None:
    config = load_vps_btc_futures_runtime_config({})

    state_path = str(config.state_repository_path)
    assert "tmp" not in state_path.lower()
    assert "user_data" not in state_path


def test_load_vps_btc_futures_runtime_config_builds_dry_run_request() -> None:
    config = load_vps_btc_futures_runtime_config(
        {
            "TRADING_FRAMEWORK_VPS_RUNTIME_ID": "vps-runtime-1",
            "TRADING_FRAMEWORK_VPS_SYMBOL": "btcusdt",
            "TRADING_FRAMEWORK_VPS_EVENT_LOG_PATH": "/data/events.jsonl",
            "TRADING_FRAMEWORK_VPS_STATE_PATH": "/data/state",
            "TRADING_FRAMEWORK_VPS_STARTING_EQUITY": "25000",
            "TRADING_FRAMEWORK_VPS_QUANTITY": "0.002",
            "TRADING_FRAMEWORK_VPS_EMA_PERIOD": "12",
            "TRADING_FRAMEWORK_VPS_EXIT_AFTER_BARS": "4",
            "TRADING_FRAMEWORK_VPS_HEARTBEAT_SECONDS": "5",
            "TRADING_FRAMEWORK_VPS_MAX_CLOSED_BARS": "50",
            "TRADING_FRAMEWORK_VPS_MAX_MESSAGES": "10",
        }
    )
    request = config.to_binance_dry_run_request()

    assert request.config.runtime_id == "vps-runtime-1"
    assert request.config.symbol == "BTCUSDT"
    assert request.config.event_log_path == Path("/data/events.jsonl")
    assert request.config.state_repository_path == Path("/data/state")
    assert request.duration_seconds == float("inf")
    assert request.heartbeat_seconds == 5
    assert request.max_closed_bars == 50
    assert request.max_messages == 10


def test_load_vps_btc_futures_runtime_config_bounded_duration_available_for_smoke_runs() -> None:
    config = load_vps_btc_futures_runtime_config({"TRADING_FRAMEWORK_VPS_DURATION_SECONDS": "60"})

    assert config.duration_seconds == 60
    assert config.is_continuous is False
    request = config.to_binance_dry_run_request()
    assert request.duration_seconds == 60


@pytest.mark.parametrize(
    "env",
    [
        {"TRADING_FRAMEWORK_VPS_QUANTITY": "0"},
        {"TRADING_FRAMEWORK_VPS_MAX_MESSAGES": "0"},
        {"TRADING_FRAMEWORK_VPS_DURATION_SECONDS": "0"},
        {"TRADING_FRAMEWORK_VPS_STARTING_EQUITY": "-1"},
    ],
)
def test_load_vps_btc_futures_runtime_config_rejects_invalid_env(env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError):
        load_vps_btc_futures_runtime_config(env)


def test_vps_btc_futures_runtime_config_rejects_blank_runtime_id() -> None:
    with pytest.raises(ConfigurationError, match="RUNTIME_ID"):
        VpsBtcFuturesRuntimeConfig(runtime_id=" ")


def test_create_vps_execution_state_repository_uses_json_backend(tmp_path: Path) -> None:
    repository = create_vps_execution_state_repository(
        VpsBtcFuturesRuntimeConfig(state_repository_path=tmp_path)
    )

    assert isinstance(repository, JsonExecutionStateRepository)
    assert repository.base_path == tmp_path


def test_run_vps_btc_futures_dry_run_passes_repository_to_binance_loop(tmp_path: Path) -> None:
    config = VpsBtcFuturesRuntimeConfig(state_repository_path=tmp_path)
    captured: dict[str, Any] = {}

    async def fake_run(request: Any, *, state_repository: Any, telemetry: Any) -> Any:
        assert request.config.runtime_id == "btc-futures-dry-run-vps"
        assert isinstance(state_repository, JsonExecutionStateRepository)
        assert telemetry is None
        captured["state_repository"] = state_repository
        return object()

    with patch(
        "trading_framework.application.execution.vps_btc_futures_runtime."
        "run_local_btc_futures_binance_dry_run",
        fake_run,
    ):
        asyncio.run(run_vps_btc_futures_dry_run(config))

    assert cast(Any, captured["state_repository"]).base_path == tmp_path


def test_run_vps_btc_futures_dry_run_stops_gracefully_on_sigterm(tmp_path: Path) -> None:
    """SIGTERM must cancel the running loop, which returns a graceful stop result."""
    config = VpsBtcFuturesRuntimeConfig(state_repository_path=tmp_path)

    async def fake_run(request: Any, *, state_repository: Any, telemetry: Any) -> str:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            return "graceful-stop-result"
        raise AssertionError("loop should have been cancelled by SIGTERM")

    async def scenario() -> Any:
        loop = asyncio.get_running_loop()
        loop.call_later(0.05, signal.raise_signal, signal.SIGTERM)
        with patch(
            "trading_framework.application.execution.vps_btc_futures_runtime."
            "run_local_btc_futures_binance_dry_run",
            fake_run,
        ):
            return await run_vps_btc_futures_dry_run(config)

    result = asyncio.run(scenario())

    assert result == "graceful-stop-result"


def test_run_vps_btc_futures_dry_run_reraises_unrecoverable_error(tmp_path: Path) -> None:
    """An unrecoverable error propagates so the entry point can exit non-zero."""
    config = VpsBtcFuturesRuntimeConfig(state_repository_path=tmp_path)

    async def fake_run(request: Any, *, state_repository: Any, telemetry: Any) -> Any:
        raise RuntimeError("simulated unrecoverable failure")

    with (
        patch(
            "trading_framework.application.execution.vps_btc_futures_runtime."
            "run_local_btc_futures_binance_dry_run",
            fake_run,
        ),
        pytest.raises(RuntimeError, match="simulated unrecoverable failure"),
    ):
        asyncio.run(run_vps_btc_futures_dry_run(config))
