"""Tests for AWS dry-run structured telemetry."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from trading_framework.application.execution import JsonCloudWatchExecutionTelemetry
from trading_framework.application.execution.local_btc_futures import LocalBtcFuturesDryRunConfig
from trading_framework.execution import Heartbeat, RuntimeHealth, RuntimeStatusSnapshot
from trading_framework.execution.modes import ExecutionMode

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def test_cloudwatch_telemetry_emits_runtime_lifecycle_json(tmp_path: Path) -> None:
    rows: list[str] = []
    telemetry = JsonCloudWatchExecutionTelemetry(writer=rows.append)
    config = LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl")

    telemetry.runtime_started(config, _status(RuntimeHealth.RUNNING))
    telemetry.runtime_stopped(config, _status(RuntimeHealth.STOPPED))

    payloads = [json.loads(row) for row in rows]
    assert [payload["event"] for payload in payloads] == ["runtime_started", "runtime_stopped"]
    assert payloads[0]["runtime_id"] == "btc-futures-dry-run-local"
    assert payloads[0]["provider"] == "binance_usdm"
    assert payloads[0]["symbol"] == "BTCUSDT"
    assert payloads[0]["simulated"] is True
    assert payloads[1]["status"] == "stopped"


def test_cloudwatch_telemetry_emits_heartbeat_emf_metric(tmp_path: Path) -> None:
    rows: list[str] = []
    telemetry = JsonCloudWatchExecutionTelemetry(writer=rows.append)
    config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "events.jsonl",
        runtime_id="aws-runtime-1",
    )

    telemetry.heartbeat_recorded(
        config,
        Heartbeat(
            runtime_id="aws-runtime-1",
            recorded_at=NOW,
            status=RuntimeHealth.RUNNING,
            message="alive",
        ),
    )

    payload = json.loads(rows[0])
    assert payload["event"] == "heartbeat_recorded"
    assert payload["heartbeat_message"] == "alive"
    assert payload["Heartbeat"] == 1
    assert payload["RuntimeId"] == "aws-runtime-1"
    assert payload["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "TradingFramework/DryRun"
    assert payload["_aws"]["CloudWatchMetrics"][0]["Metrics"][0]["Name"] == "Heartbeat"


def _status(status: RuntimeHealth) -> RuntimeStatusSnapshot:
    return RuntimeStatusSnapshot(
        runtime_id="btc-futures-dry-run-local",
        mode=ExecutionMode.DRY_RUN,
        status=status,
        provider="binance_usdm",
        symbol="BTCUSDT",
        last_heartbeat_at=NOW,
    )
