"""Tests for the VPS BTC futures dry-run worker entry point."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts.execution import run_vps_btc_futures_worker

from trading_framework.application.execution import LocalBtcFuturesBinanceFeedState
from trading_framework.core.exceptions import IncompatibleExecutionStateError
from trading_framework.execution import RuntimeHealth, RuntimeStatusSnapshot
from trading_framework.execution.modes import ExecutionMode

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FakeRuntimeConfig:
    runtime_id: str
    symbol: str
    event_log_path: Path


@dataclass(frozen=True, slots=True)
class FakeRuntime:
    config: FakeRuntimeConfig


@dataclass(frozen=True, slots=True)
class FakeResult:
    runtime: FakeRuntime
    stopped_status: RuntimeStatusSnapshot
    feed_state: LocalBtcFuturesBinanceFeedState
    received_message_count: int


def test_vps_btc_futures_worker_cli_loads_env_and_runs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("TRADING_FRAMEWORK_VPS_DURATION_SECONDS", raising=False)
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_RUNTIME_ID", "vps-runtime-1")
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_SYMBOL", "btcusdt")

    def fake_run(config: Any) -> FakeResult:
        assert config.runtime_id == "vps-runtime-1"
        assert config.symbol == "BTCUSDT"
        assert config.is_continuous is True
        return FakeResult(
            runtime=FakeRuntime(
                config=FakeRuntimeConfig(
                    runtime_id=config.runtime_id,
                    symbol=config.symbol,
                    event_log_path=config.event_log_path,
                )
            ),
            stopped_status=RuntimeStatusSnapshot(
                runtime_id=config.runtime_id,
                mode=ExecutionMode.DRY_RUN,
                status=RuntimeHealth.STOPPED,
                provider="binance_usdm",
                symbol=config.symbol,
                last_heartbeat_at=NOW,
            ),
            feed_state=LocalBtcFuturesBinanceFeedState(
                closed_bar_count=2,
                ignored_message_count=1,
            ),
            received_message_count=3,
        )

    with patch.object(run_vps_btc_futures_worker, "run_vps_btc_futures_dry_run_sync", fake_run):
        exit_code = run_vps_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert '"event": "vps_worker_summary"' in captured.out
    assert '"runtime_id": "vps-runtime-1"' in captured.out
    assert '"continuous": true' in captured.out
    assert '"simulated": true' in captured.out


def test_vps_btc_futures_worker_cli_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TRADING_FRAMEWORK_VPS_QUANTITY", "0")

    exit_code = run_vps_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "QUANTITY" in captured.err


def test_vps_btc_futures_worker_cli_exits_distinctly_on_refuse_to_start(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("TRADING_FRAMEWORK_VPS_QUANTITY", raising=False)

    def fake_run(config: Any) -> FakeResult:
        raise IncompatibleExecutionStateError("persisted execution state is incompatible")

    with patch.object(run_vps_btc_futures_worker, "run_vps_btc_futures_dry_run_sync", fake_run):
        exit_code = run_vps_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "incompatible" in captured.err


def test_vps_btc_futures_worker_cli_reports_unrecoverable_non_framework_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-TradingFrameworkError failure (e.g. network/OS error) must still exit

    non-zero with a single clean stderr line, not an uncaught traceback that
    could print internal container paths (ADR-0035 SS4.3, SS4.7).
    """
    monkeypatch.delenv("TRADING_FRAMEWORK_VPS_QUANTITY", raising=False)

    def fake_run(config: Any) -> FakeResult:
        raise ConnectionError("simulated feed connection failure")

    with patch.object(run_vps_btc_futures_worker, "run_vps_btc_futures_dry_run_sync", fake_run):
        exit_code = run_vps_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "simulated feed connection failure" in captured.err
    assert "Traceback" not in captured.err
