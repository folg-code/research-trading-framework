"""Tests for `trading-cli dry-run start` (S046-T008).

Tier 1, network-free: fakes the application-layer entry point (the same
pattern as tests/unit/scripts/test_btc_futures_dry_run_cli.py). The runtime
itself already has its own coverage; this test proves the CLI seam (config ->
typed request -> printed result) and the event-loop entry (SPRINT_046.md §4
finding 4): `trading_cli.cli.main` is synchronous, so `asyncio.run()` inside
`dry_run.run()` is never called from within a running loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from trading_framework.application.execution import LocalBtcFuturesBinanceFeedState
from trading_framework.execution import RuntimeHealth, RuntimeStatusSnapshot
from trading_framework.execution.modes import ExecutionMode

from trading_cli.cli import main
from trading_cli.commands import dry_run as dry_run_cmd
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _write_config(tmp_path: Path, *, storage_root: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text.format(storage_root=storage_root.as_posix()), encoding="utf-8")
    return path


@dataclass(frozen=True, slots=True)
class _FakeRuntimeConfig:
    runtime_id: str
    symbol: str
    event_log_path: Path


@dataclass(frozen=True, slots=True)
class _FakeRuntime:
    config: _FakeRuntimeConfig


@dataclass(frozen=True, slots=True)
class _FakeResult:
    runtime: _FakeRuntime
    stopped_status: RuntimeStatusSnapshot
    feed_state: LocalBtcFuturesBinanceFeedState
    received_message_count: int


def test_dry_run_start_runs_with_config_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    event_log = tmp_path / "events.jsonl"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "dry_run:\n"
            "  symbol: BTCUSDT\n"
            "  duration_minutes: 0.1\n"
            f"  event_log: {event_log.as_posix()}\n"
        ),
    )
    captured: dict[str, Any] = {}

    async def fake_run(request: Any) -> _FakeResult:
        captured["duration_seconds"] = request.duration_seconds
        captured["symbol"] = request.config.symbol
        captured["event_log_path"] = request.config.event_log_path
        return _FakeResult(
            runtime=_FakeRuntime(
                config=_FakeRuntimeConfig(
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
                last_heartbeat_at=_NOW,
            ),
            feed_state=LocalBtcFuturesBinanceFeedState(
                closed_bar_count=2,
                ignored_message_count=0,
            ),
            received_message_count=5,
        )

    with patch.object(dry_run_cmd, "run_local_btc_futures_binance_dry_run", fake_run):
        exit_code = main(["dry-run", "start", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    assert captured["duration_seconds"] == pytest.approx(6.0)
    assert captured["symbol"] == "BTCUSDT"
    assert captured["event_log_path"] == event_log
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "stopped"
    assert payload["result"]["received_messages"] == 5


def test_dry_run_start_missing_duration_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="version: 1\nstorage_root: {storage_root}\n\ndry_run:\n  symbol: BTCUSDT\n",
    )

    exit_code = main(["dry-run", "start", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_dry_run_start_negative_duration_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=("version: 1\nstorage_root: {storage_root}\n\ndry_run:\n  duration_minutes: -1\n"),
    )

    exit_code = main(["dry-run", "start", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR
