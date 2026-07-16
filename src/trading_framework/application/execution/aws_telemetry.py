"""Structured telemetry for the AWS BTC futures dry-run worker."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, final

from trading_framework.application.execution.binance_local_btc_futures import (
    LocalBtcFuturesBinanceMessageResult,
)
from trading_framework.application.execution.local_btc_futures import LocalBtcFuturesDryRunConfig
from trading_framework.execution.models import Heartbeat, RuntimeStatusSnapshot

DEFAULT_CLOUDWATCH_NAMESPACE = "TradingFramework/DryRun"


class ExecutionTelemetrySink(Protocol):
    """Observer for dry-run runtime lifecycle telemetry."""

    def runtime_started(
        self, config: LocalBtcFuturesDryRunConfig, status: RuntimeStatusSnapshot
    ) -> None:
        """Record that the runtime started."""
        ...

    def heartbeat_recorded(self, config: LocalBtcFuturesDryRunConfig, heartbeat: Heartbeat) -> None:
        """Record a runtime heartbeat."""
        ...

    def market_message_processed(
        self,
        config: LocalBtcFuturesDryRunConfig,
        result: LocalBtcFuturesBinanceMessageResult,
        *,
        received_message_count: int,
    ) -> None:
        """Record one processed or ignored market-data message."""
        ...

    def runtime_stopped(
        self, config: LocalBtcFuturesDryRunConfig, status: RuntimeStatusSnapshot
    ) -> None:
        """Record that the runtime stopped."""
        ...


@final
@dataclass(frozen=True, slots=True)
class JsonCloudWatchExecutionTelemetry:
    """Emit CloudWatch-friendly structured JSON logs and heartbeat EMF metrics."""

    writer: Callable[[str], None] = print
    namespace: str = DEFAULT_CLOUDWATCH_NAMESPACE

    def runtime_started(
        self, config: LocalBtcFuturesDryRunConfig, status: RuntimeStatusSnapshot
    ) -> None:
        """Record that the runtime started."""
        self._write(
            "runtime_started",
            config=config,
            status=status.status.value,
            occurred_at=status.last_heartbeat_at,
        )

    def heartbeat_recorded(self, config: LocalBtcFuturesDryRunConfig, heartbeat: Heartbeat) -> None:
        """Record a runtime heartbeat with a CloudWatch EMF metric."""
        self._write(
            "heartbeat_recorded",
            config=config,
            status=heartbeat.status.value,
            occurred_at=heartbeat.recorded_at,
            extra={
                "heartbeat_message": heartbeat.message,
                **_heartbeat_metric(
                    namespace=self.namespace,
                    timestamp=heartbeat.recorded_at,
                    runtime_id=config.runtime_id,
                    provider=config.provider,
                    symbol=config.symbol,
                ),
            },
        )

    def market_message_processed(
        self,
        config: LocalBtcFuturesDryRunConfig,
        result: LocalBtcFuturesBinanceMessageResult,
        *,
        received_message_count: int,
    ) -> None:
        """Record one processed or ignored market-data message."""
        self._write(
            "market_message_processed",
            config=config,
            status="processed" if result.processed_closed_bar else "ignored",
            extra={
                "received_messages": received_message_count,
                "closed_bars": result.state.closed_bar_count,
                "ignored_messages": result.state.ignored_message_count,
                "ignored_reason": result.ignored_reason,
            },
        )

    def runtime_stopped(
        self, config: LocalBtcFuturesDryRunConfig, status: RuntimeStatusSnapshot
    ) -> None:
        """Record that the runtime stopped."""
        self._write(
            "runtime_stopped",
            config=config,
            status=status.status.value,
            occurred_at=status.last_heartbeat_at,
        )

    def _write(
        self,
        event: str,
        *,
        config: LocalBtcFuturesDryRunConfig,
        status: str,
        occurred_at: datetime | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "runtime_id": config.runtime_id,
            "provider": config.provider,
            "symbol": config.symbol,
            "status": status,
            "simulated": True,
        }
        if occurred_at is not None:
            payload["occurred_at"] = occurred_at.isoformat()
        if extra is not None:
            payload.update({key: value for key, value in extra.items() if value is not None})
        self.writer(json.dumps(payload, sort_keys=True))


def _heartbeat_metric(
    *,
    namespace: str,
    timestamp: datetime,
    runtime_id: str,
    provider: str,
    symbol: str,
) -> dict[str, Any]:
    return {
        "_aws": {
            "Timestamp": int(timestamp.timestamp() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": namespace,
                    "Dimensions": [["RuntimeId", "Provider", "Symbol"]],
                    "Metrics": [{"Name": "Heartbeat", "Unit": "Count"}],
                }
            ],
        },
        "RuntimeId": runtime_id,
        "Provider": provider,
        "Symbol": symbol,
        "Heartbeat": 1,
    }
