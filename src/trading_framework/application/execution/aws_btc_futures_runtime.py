"""AWS runtime configuration for the BTCUSDT futures dry-run worker."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import final

from trading_framework.application.execution.binance_local_btc_futures import (
    RunLocalBtcFuturesBinanceDryRunRequest,
    RunLocalBtcFuturesBinanceDryRunResult,
    run_local_btc_futures_binance_dry_run,
)
from trading_framework.application.execution.local_btc_futures import (
    LocalBtcFuturesDryRunConfig,
)
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.strategy import BtcFuturesDemoStrategyConfig

AWS_RUNTIME_ENV_PREFIX = "TRADING_FRAMEWORK_"
DEFAULT_AWS_RUNTIME_ID = "btc-futures-dry-run-aws"
DEFAULT_AWS_EVENT_LOG_PATH = Path("/tmp/trading_framework/btc_futures_dry_run/events.jsonl")
DEFAULT_AWS_STATE_REPOSITORY_PATH = Path("/tmp/trading_framework/btc_futures_dry_run/state")


@final
@dataclass(frozen=True, slots=True)
class AwsBtcFuturesRuntimeConfig:
    """Validated environment-backed configuration for the AWS dry-run worker."""

    aws_region: str
    execution_state_table_name: str
    runtime_id: str = DEFAULT_AWS_RUNTIME_ID
    symbol: str = "BTCUSDT"
    event_log_path: Path = DEFAULT_AWS_EVENT_LOG_PATH
    state_repository_path: Path = DEFAULT_AWS_STATE_REPOSITORY_PATH
    starting_equity: Decimal = Decimal("10000")
    quantity: Decimal = Decimal("0.001")
    ema_period: int = 20
    exit_after_bars: int = 10
    duration_seconds: float = 3600.0
    heartbeat_seconds: float = 30.0
    max_closed_bars: int = 200
    max_messages: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "aws_region", _non_empty(self.aws_region, "AWS_REGION"))
        object.__setattr__(
            self,
            "execution_state_table_name",
            _non_empty(self.execution_state_table_name, "EXECUTION_STATE_TABLE"),
        )
        object.__setattr__(self, "runtime_id", _non_empty(self.runtime_id, "RUNTIME_ID"))
        object.__setattr__(self, "symbol", _non_empty(self.symbol, "SYMBOL").upper())
        if self.starting_equity <= 0:
            raise ConfigurationError("STARTING_EQUITY must be positive")
        if self.quantity <= 0:
            raise ConfigurationError("QUANTITY must be positive")
        if self.ema_period < 1:
            raise ConfigurationError("EMA_PERIOD must be positive")
        if self.exit_after_bars < 1:
            raise ConfigurationError("EXIT_AFTER_BARS must be positive")
        if self.duration_seconds <= 0:
            raise ConfigurationError("DURATION_SECONDS must be positive")
        if self.heartbeat_seconds <= 0:
            raise ConfigurationError("HEARTBEAT_SECONDS must be positive")
        if self.max_closed_bars < 1:
            raise ConfigurationError("MAX_CLOSED_BARS must be positive")
        if self.max_messages is not None and self.max_messages < 1:
            raise ConfigurationError("MAX_MESSAGES must be positive when provided")

    def to_binance_dry_run_request(self) -> RunLocalBtcFuturesBinanceDryRunRequest:
        """Build the current Binance-backed dry-run request."""
        return RunLocalBtcFuturesBinanceDryRunRequest(
            config=LocalBtcFuturesDryRunConfig(
                event_log_path=self.event_log_path,
                state_repository_path=self.state_repository_path,
                runtime_id=self.runtime_id,
                symbol=self.symbol,
                starting_equity=self.starting_equity,
                strategy_config=BtcFuturesDemoStrategyConfig(
                    ema_period=self.ema_period,
                    exit_after_bars=self.exit_after_bars,
                    quantity=self.quantity,
                ),
            ),
            duration_seconds=self.duration_seconds,
            heartbeat_seconds=self.heartbeat_seconds,
            max_closed_bars=self.max_closed_bars,
            max_messages=self.max_messages,
        )


def load_aws_btc_futures_runtime_config(
    env: Mapping[str, str],
) -> AwsBtcFuturesRuntimeConfig:
    """Load AWS dry-run worker configuration from environment variables."""
    return AwsBtcFuturesRuntimeConfig(
        aws_region=_required(env, "AWS_REGION"),
        execution_state_table_name=_required(env, "EXECUTION_STATE_TABLE"),
        runtime_id=_optional(env, "RUNTIME_ID", DEFAULT_AWS_RUNTIME_ID),
        symbol=_optional(env, "SYMBOL", "BTCUSDT"),
        event_log_path=Path(_optional(env, "EVENT_LOG_PATH", str(DEFAULT_AWS_EVENT_LOG_PATH))),
        state_repository_path=Path(
            _optional(env, "STATE_REPOSITORY_PATH", str(DEFAULT_AWS_STATE_REPOSITORY_PATH))
        ),
        starting_equity=_decimal(env, "STARTING_EQUITY", Decimal("10000")),
        quantity=_decimal(env, "QUANTITY", Decimal("0.001")),
        ema_period=_int(env, "EMA_PERIOD", 20),
        exit_after_bars=_int(env, "EXIT_AFTER_BARS", 10),
        duration_seconds=_float(env, "DURATION_SECONDS", 3600.0),
        heartbeat_seconds=_float(env, "HEARTBEAT_SECONDS", 30.0),
        max_closed_bars=_int(env, "MAX_CLOSED_BARS", 200),
        max_messages=_optional_int(env, "MAX_MESSAGES"),
    )


async def run_aws_btc_futures_dry_run(
    config: AwsBtcFuturesRuntimeConfig,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run the AWS worker's current Binance dry-run lifecycle."""
    return await run_local_btc_futures_binance_dry_run(config.to_binance_dry_run_request())


def run_aws_btc_futures_dry_run_sync(
    config: AwsBtcFuturesRuntimeConfig,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run the AWS worker from a synchronous container entry point."""
    return asyncio.run(run_aws_btc_futures_dry_run(config))


def _key(name: str) -> str:
    return f"{AWS_RUNTIME_ENV_PREFIX}{name}"


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(_key(name))
    if value is None or not value.strip():
        raise ConfigurationError(f"{_key(name)} is required")
    return value


def _optional(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(_key(name))
    if value is None or not value.strip():
        return default
    return value


def _decimal(env: Mapping[str, str], name: str, default: Decimal) -> Decimal:
    raw = _optional(env, name, str(default))
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ConfigurationError(f"{_key(name)} must be a decimal") from exc


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _optional(env, name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{_key(name)} must be an integer") from exc


def _optional_int(env: Mapping[str, str], name: str) -> int | None:
    raw = env.get(_key(name))
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{_key(name)} must be an integer") from exc


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = _optional(env, name, str(default))
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{_key(name)} must be a number") from exc


def _non_empty(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ConfigurationError(f"{name} must be non-empty")
    return normalized
