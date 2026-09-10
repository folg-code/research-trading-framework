"""VPS runtime configuration for the BTCUSDT futures dry-run worker.

Provider-neutral entry point over the existing local/Binance dry-run runtime
(:mod:`trading_framework.application.execution.local_btc_futures` and
:mod:`trading_framework.application.execution.binance_local_btc_futures`) and
:class:`JsonExecutionStateRepository`. See
``docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md`` for the
binding contract this module implements (SS1.6, SS4.1, SS4.4).

Unlike :mod:`trading_framework.application.execution.aws_btc_futures_runtime`,
this configuration requires no AWS-specific value to start (no
``AWS_REGION``, no ``EXECUTION_STATE_TABLE``), defaults to a continuous
service lifetime rather than a bounded one-hour task, defaults its state path
under a dedicated VPS volume rather than ``/tmp``, and only ever uses the
JSON execution state backend (no DynamoDB option).
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import signal
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import final

from trading_framework.application.execution.binance_local_btc_futures import (
    LocalBtcFuturesBinanceTelemetrySink,
    RunLocalBtcFuturesBinanceDryRunRequest,
    RunLocalBtcFuturesBinanceDryRunResult,
    run_local_btc_futures_binance_dry_run,
)
from trading_framework.application.execution.local_btc_futures import (
    LocalBtcFuturesDryRunConfig,
)
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.execution import ExecutionStateRepository
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository
from trading_framework.strategy import BtcFuturesDemoStrategyConfig

VPS_RUNTIME_ENV_PREFIX = "TRADING_FRAMEWORK_VPS_"
DEFAULT_VPS_RUNTIME_ID = "btc-futures-dry-run-vps"
DEFAULT_VPS_SYMBOL = "BTCUSDT"
# Dedicated execution-state volume path (ADR-0035 SS2: not /tmp, not user_data).
DEFAULT_VPS_EVENT_LOG_PATH = Path("/var/lib/trading-framework/btc-futures-dry-run/events.jsonl")
DEFAULT_VPS_STATE_REPOSITORY_PATH = Path("/var/lib/trading-framework/btc-futures-dry-run/state")


@final
@dataclass(frozen=True, slots=True)
class VpsBtcFuturesRuntimeConfig:
    """Validated environment-backed configuration for the VPS dry-run worker.

    Provider-neutral (ADR-0035 D062-02): starting this configuration never
    requires an AWS-specific value. Defaults to a continuous/unbounded
    service lifetime (``duration_seconds=None``); a bounded duration remains
    available for smoke testing only, never as the default (ADR-0035 SS4.1).
    """

    runtime_id: str = DEFAULT_VPS_RUNTIME_ID
    symbol: str = DEFAULT_VPS_SYMBOL
    event_log_path: Path = DEFAULT_VPS_EVENT_LOG_PATH
    state_repository_path: Path = DEFAULT_VPS_STATE_REPOSITORY_PATH
    starting_equity: Decimal = Decimal("10000")
    quantity: Decimal = Decimal("0.001")
    ema_period: int = 20
    exit_after_bars: int = 10
    duration_seconds: float | None = None
    heartbeat_seconds: float = 30.0
    max_closed_bars: int = 200
    max_messages: int | None = None

    def __post_init__(self) -> None:
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
        if self.duration_seconds is not None and self.duration_seconds <= 0:
            raise ConfigurationError("DURATION_SECONDS must be positive when provided")
        if self.heartbeat_seconds <= 0:
            raise ConfigurationError("HEARTBEAT_SECONDS must be positive")
        if self.max_closed_bars < 1:
            raise ConfigurationError("MAX_CLOSED_BARS must be positive")
        if self.max_messages is not None and self.max_messages < 1:
            raise ConfigurationError("MAX_MESSAGES must be positive when provided")

    @property
    def is_continuous(self) -> bool:
        """Whether this configuration runs as an unbounded continuous service."""
        return self.duration_seconds is None

    def to_binance_dry_run_request(self) -> RunLocalBtcFuturesBinanceDryRunRequest:
        """Build the current Binance-backed dry-run request.

        An unset ``duration_seconds`` (continuous service) is translated to
        an unbounded ``math.inf`` duration for the existing bounded-loop
        request type, so the existing loop implementation is reused
        unchanged rather than rewritten for an unbounded case.
        """
        effective_duration = math.inf if self.duration_seconds is None else self.duration_seconds
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
            duration_seconds=effective_duration,
            heartbeat_seconds=self.heartbeat_seconds,
            max_closed_bars=self.max_closed_bars,
            max_messages=self.max_messages,
        )


def load_vps_btc_futures_runtime_config(env: Mapping[str, str]) -> VpsBtcFuturesRuntimeConfig:
    """Load VPS dry-run worker configuration from environment variables.

    Requires no AWS-specific value (ADR-0035 D062-02): there is no
    ``AWS_REGION`` or ``EXECUTION_STATE_TABLE`` variable in this contract.
    Leaving ``TRADING_FRAMEWORK_VPS_DURATION_SECONDS`` unset selects the
    default continuous/unbounded service lifetime.
    """
    return VpsBtcFuturesRuntimeConfig(
        runtime_id=_optional(env, "RUNTIME_ID", DEFAULT_VPS_RUNTIME_ID),
        symbol=_optional(env, "SYMBOL", DEFAULT_VPS_SYMBOL),
        event_log_path=Path(_optional(env, "EVENT_LOG_PATH", str(DEFAULT_VPS_EVENT_LOG_PATH))),
        state_repository_path=Path(
            _optional(env, "STATE_PATH", str(DEFAULT_VPS_STATE_REPOSITORY_PATH))
        ),
        starting_equity=_decimal(env, "STARTING_EQUITY", Decimal("10000")),
        quantity=_decimal(env, "QUANTITY", Decimal("0.001")),
        ema_period=_int(env, "EMA_PERIOD", 20),
        exit_after_bars=_int(env, "EXIT_AFTER_BARS", 10),
        duration_seconds=_optional_float(env, "DURATION_SECONDS"),
        heartbeat_seconds=_float(env, "HEARTBEAT_SECONDS", 30.0),
        max_closed_bars=_int(env, "MAX_CLOSED_BARS", 200),
        max_messages=_optional_int(env, "MAX_MESSAGES"),
    )


async def run_vps_btc_futures_dry_run(
    config: VpsBtcFuturesRuntimeConfig,
    *,
    telemetry: LocalBtcFuturesBinanceTelemetrySink | None = None,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run the VPS worker's dry-run lifecycle (continuous by default).

    ``SIGTERM``/``SIGINT`` request graceful shutdown: the reused loop
    persists a final ``STOPPED`` status and this coroutine returns normally
    (ADR-0035 SS4.2). An unrecoverable error persists ``FAILED`` on a
    best-effort basis and re-raises (ADR-0035 SS4.3), so the synchronous
    entry point can exit non-zero. Incompatible or unreadable persisted
    state raises ``IncompatibleExecutionStateError`` before the runtime
    starts (ADR-0035 SS4.4); this coroutine does not catch it.
    """
    repository = create_vps_execution_state_repository(config)
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    if task is None:
        msg = "run_vps_btc_futures_dry_run must run inside a task"
        raise RuntimeError(msg)

    def _request_stop() -> None:
        task.cancel()

    registered: list[int] = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _request_stop)
            registered.append(int(sig))
        except (NotImplementedError, RuntimeError, ValueError):
            # Windows / restricted loops: fall back to signal.signal when possible.
            try:
                signal.signal(sig, lambda *_args: _request_stop())
                registered.append(int(sig))
            except (ValueError, OSError):
                continue
    try:
        return await run_local_btc_futures_binance_dry_run(
            config.to_binance_dry_run_request(),
            state_repository=repository,
            telemetry=telemetry,
        )
    finally:
        for sig_num in registered:
            with contextlib.suppress(NotImplementedError, RuntimeError, ValueError):
                loop.remove_signal_handler(sig_num)


def run_vps_btc_futures_dry_run_sync(
    config: VpsBtcFuturesRuntimeConfig,
    *,
    telemetry: LocalBtcFuturesBinanceTelemetrySink | None = None,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run the VPS worker from a synchronous container entry point."""
    return asyncio.run(run_vps_btc_futures_dry_run(config, telemetry=telemetry))


def create_vps_execution_state_repository(
    config: VpsBtcFuturesRuntimeConfig,
) -> ExecutionStateRepository:
    """Create the JSON execution state repository for the VPS dry-run worker."""
    return JsonExecutionStateRepository(config.state_repository_path)


def _key(name: str) -> str:
    return f"{VPS_RUNTIME_ENV_PREFIX}{name}"


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


def _optional_float(env: Mapping[str, str], name: str) -> float | None:
    raw = env.get(_key(name))
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{_key(name)} must be a number") from exc


def _non_empty(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ConfigurationError(f"{name} must be non-empty")
    return normalized
