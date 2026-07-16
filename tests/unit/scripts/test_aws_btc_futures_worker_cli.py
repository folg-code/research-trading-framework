"""Tests for the AWS BTC futures dry-run worker entry point."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts.execution import run_aws_btc_futures_worker

from trading_framework.application.execution import LocalBtcFuturesBinanceFeedState
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


def test_aws_btc_futures_worker_cli_loads_env_and_runs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TRADING_FRAMEWORK_AWS_REGION", "eu-central-1")
    monkeypatch.setenv("TRADING_FRAMEWORK_EXECUTION_STATE_TABLE", "demo-execution-state")
    monkeypatch.setenv("TRADING_FRAMEWORK_RUNTIME_ID", "aws-runtime-1")
    monkeypatch.setenv("TRADING_FRAMEWORK_SYMBOL", "btcusdt")
    monkeypatch.setenv("TRADING_FRAMEWORK_DURATION_SECONDS", "60")

    def fake_run(config: Any, *, telemetry: Any) -> FakeResult:
        assert config.aws_region == "eu-central-1"
        assert config.execution_state_table_name == "demo-execution-state"
        assert config.runtime_id == "aws-runtime-1"
        assert config.symbol == "BTCUSDT"
        assert config.duration_seconds == 60
        assert telemetry is not None
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

    with patch.object(run_aws_btc_futures_worker, "run_aws_btc_futures_dry_run_sync", fake_run):
        exit_code = run_aws_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert '"event": "aws_worker_summary"' in captured.out
    assert '"runtime_id": "aws-runtime-1"' in captured.out
    assert '"aws_region": "eu-central-1"' in captured.out
    assert '"execution_state_backend": "dynamodb"' in captured.out
    assert '"execution_state_table": "demo-execution-state"' in captured.out
    assert '"simulated": true' in captured.out


def test_aws_btc_futures_worker_cli_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("TRADING_FRAMEWORK_AWS_REGION", raising=False)
    monkeypatch.delenv("TRADING_FRAMEWORK_EXECUTION_STATE_TABLE", raising=False)

    exit_code = run_aws_btc_futures_worker.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "TRADING_FRAMEWORK_AWS_REGION is required" in captured.err
