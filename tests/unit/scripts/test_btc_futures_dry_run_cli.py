"""CLI tests for the local BTC futures dry-run command."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts.execution import run_btc_futures_dry_run

from trading_framework.application.execution import LocalBtcFuturesBinanceFeedState
from trading_framework.execution import RuntimeHealth, RuntimeStatusSnapshot
from trading_framework.execution.modes import ExecutionMode

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


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


def test_btc_futures_dry_run_cli_runs_with_bounded_arguments(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    event_log = tmp_path / "events.jsonl"

    async def fake_run(request: Any) -> FakeResult:
        assert request.duration_seconds == 6
        assert request.heartbeat_seconds == 2
        assert request.max_closed_bars == 5
        assert request.max_messages == 3
        assert request.config.event_log_path == event_log
        assert request.config.symbol == "BTCUSDT"
        assert request.config.strategy_config.quantity == Decimal("0.002")
        return FakeResult(
            runtime=FakeRuntime(
                config=FakeRuntimeConfig(
                    runtime_id=request.config.runtime_id,
                    symbol=request.config.symbol,
                    event_log_path=request.config.event_log_path,
                )
            ),
            stopped_status=RuntimeStatusSnapshot(
                runtime_id=request.config.runtime_id,
                mode=ExecutionMode.DRY_RUN,
                status=RuntimeHealth.STOPPED,
                provider="binance_usdm",
                symbol=request.config.symbol,
                last_heartbeat_at=NOW,
            ),
            feed_state=LocalBtcFuturesBinanceFeedState(
                closed_bar_count=2,
                ignored_message_count=1,
            ),
            received_message_count=3,
        )

    with patch.object(
        run_btc_futures_dry_run,
        "run_local_btc_futures_binance_dry_run",
        fake_run,
    ):
        exit_code = run_btc_futures_dry_run.main(
            [
                "--event-log",
                str(event_log),
                "--duration-minutes",
                "0.1",
                "--heartbeat-seconds",
                "2",
                "--quantity",
                "0.002",
                "--max-closed-bars",
                "5",
                "--max-messages",
                "3",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"event": "summary"' in output
    assert '"status": "stopped"' in output
    assert '"simulated": true' in output
    assert '"received_messages": 3' in output
    assert '"closed_bars": 2' in output
    assert '"ignored_messages": 1' in output


def test_btc_futures_dry_run_cli_rejects_invalid_duration(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    exit_code = run_btc_futures_dry_run.main(
        [
            "--event-log",
            str(tmp_path / "events.jsonl"),
            "--duration-minutes",
            "-1",
        ]
    )

    error = capsys.readouterr().err
    assert exit_code == 1
    assert "duration_minutes" in error
