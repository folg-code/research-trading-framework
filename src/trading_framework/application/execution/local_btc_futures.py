"""Local BTCUSDT futures dry-run runtime assembly."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution import (
    EmaMomentumLiveSignalEvaluator,
    LiveSignalEvaluation,
    LocalExecutionRuntimeSession,
    PaperBroker,
    PaperBrokerState,
    RuntimeDecisionStep,
    RuntimeDecisionStepResult,
    RuntimeStatusSnapshot,
    StrategyModelOrderAdapter,
    closed_bar_close_reference_quote,
)
from trading_framework.execution.models import Heartbeat
from trading_framework.infrastructure.storage.execution_events import JsonlExecutionEventSink
from trading_framework.market.models import MarketBar
from trading_framework.strategy import (
    BTC_FUTURES_DEMO_DISCLOSURE,
    BtcFuturesDemoStrategyConfig,
    build_btc_futures_demo_strategy_model,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

DEFAULT_LOCAL_BTC_FUTURES_RUNTIME_ID = "btc-futures-dry-run-local"
DEFAULT_BINANCE_USDM_PROVIDER = "binance_usdm"
DEFAULT_BTCUSDT_SYMBOL = "BTCUSDT"
DEFAULT_PAPER_ACCOUNT_ID = "paper-btc-futures"
DEFAULT_PAPER_CURRENCY = "USDT"
DEFAULT_STARTING_EQUITY = Decimal("10000")


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesDryRunConfig:
    """Configuration for local BTCUSDT futures dry-run runtime assembly."""

    event_log_path: Path
    runtime_id: str = DEFAULT_LOCAL_BTC_FUTURES_RUNTIME_ID
    provider: str = DEFAULT_BINANCE_USDM_PROVIDER
    symbol: str = DEFAULT_BTCUSDT_SYMBOL
    account_id: str = DEFAULT_PAPER_ACCOUNT_ID
    currency: str = DEFAULT_PAPER_CURRENCY
    starting_equity: Decimal = DEFAULT_STARTING_EQUITY
    strategy_config: BtcFuturesDemoStrategyConfig | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_id", _normalize_non_empty(self.runtime_id, "runtime_id"))
        object.__setattr__(self, "provider", _normalize_non_empty(self.provider, "provider"))
        object.__setattr__(self, "symbol", _normalize_non_empty(self.symbol, "symbol").upper())
        object.__setattr__(self, "account_id", _normalize_non_empty(self.account_id, "account_id"))
        object.__setattr__(
            self,
            "currency",
            _normalize_non_empty(self.currency, "currency").upper(),
        )
        if self.starting_equity <= 0:
            msg = "starting_equity must be positive"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesDryRunRuntime:
    """Assembled local BTCUSDT futures dry-run runtime components."""

    config: LocalBtcFuturesDryRunConfig
    session: LocalExecutionRuntimeSession
    broker: PaperBroker
    decision_step: RuntimeDecisionStep
    signal_evaluator: EmaMomentumLiveSignalEvaluator
    initial_state: PaperBrokerState


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesClosedBarStepResult:
    """Result of one closed-bar local BTCUSDT dry-run step."""

    signal_evaluation: LiveSignalEvaluation
    decision_result: RuntimeDecisionStepResult
    broker_state: PaperBrokerState


@final
@dataclass(frozen=True, slots=True)
class RunLocalBtcFuturesDryRunRequest:
    """Request for a bounded local BTCUSDT futures dry-run lifecycle."""

    config: LocalBtcFuturesDryRunConfig
    duration_minutes: float
    heartbeat_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.duration_minutes < 0:
            msg = "duration_minutes must be non-negative"
            raise ValidationError(msg)
        if self.heartbeat_seconds <= 0:
            msg = "heartbeat_seconds must be positive"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class RunLocalBtcFuturesDryRunResult:
    """Result of a bounded local BTCUSDT futures dry-run lifecycle."""

    runtime: LocalBtcFuturesDryRunRuntime
    started_status: RuntimeStatusSnapshot
    heartbeat: Heartbeat
    stopped_status: RuntimeStatusSnapshot


def create_local_btc_futures_dry_run_runtime(
    config: LocalBtcFuturesDryRunConfig,
    *,
    clock: Clock | None = None,
) -> LocalBtcFuturesDryRunRuntime:
    """Assemble local dry-run runtime components without starting live IO."""
    runtime_clock = clock or SystemClock()
    event_sink = JsonlExecutionEventSink(config.event_log_path)
    session = LocalExecutionRuntimeSession(
        runtime_id=config.runtime_id,
        provider=config.provider,
        symbol=config.symbol,
        event_sink=event_sink,
        clock=runtime_clock,
    )
    broker = PaperBroker(
        account_id=config.account_id,
        symbol=config.symbol,
        currency=config.currency,
        starting_equity=config.starting_equity,
    )
    strategy_config = config.strategy_config or BtcFuturesDemoStrategyConfig()
    strategy_model = build_btc_futures_demo_strategy_model(strategy_config)
    signal_evaluator = EmaMomentumLiveSignalEvaluator(strategy_model)
    strategy_adapter = StrategyModelOrderAdapter(
        strategy_model=strategy_model,
        symbol=config.symbol,
        disclosure=strategy_config.disclosure or BTC_FUTURES_DEMO_DISCLOSURE,
    )
    decision_step = RuntimeDecisionStep(
        session=session,
        strategy_adapter=strategy_adapter,
        broker=broker,
    )
    initial_state = broker.initial_state(runtime_clock.now())
    return LocalBtcFuturesDryRunRuntime(
        config=config,
        session=session,
        broker=broker,
        decision_step=decision_step,
        signal_evaluator=signal_evaluator,
        initial_state=initial_state,
    )


def run_local_btc_futures_closed_bar_step(
    runtime: LocalBtcFuturesDryRunRuntime,
    closed_bars: tuple[MarketBar, ...],
) -> LocalBtcFuturesClosedBarStepResult:
    """Run one deterministic closed-bar dry-run step."""
    if not closed_bars:
        msg = "closed_bars must contain at least one bar"
        raise ValidationError(msg)
    latest_bar = closed_bars[-1]
    signal_evaluation = runtime.signal_evaluator.evaluate(closed_bars)
    quote = closed_bar_close_reference_quote(
        symbol=runtime.config.symbol,
        bar=latest_bar,
    )
    broker_state_before_decision = runtime.broker.mark_to_market(
        latest_bar.close,
        latest_bar.available_at,
    )
    decision_result = runtime.decision_step.run(
        entry_signal_active=signal_evaluation.entry_signal_active,
        exit_signal_active=signal_evaluation.exit_signal_active,
        position=broker_state_before_decision.position,
        quote=quote,
    )
    broker_state = (
        PaperBrokerState(
            account=decision_result.broker_result.account,
            position=decision_result.broker_result.position,
        )
        if decision_result.broker_result is not None
        else broker_state_before_decision
    )
    return LocalBtcFuturesClosedBarStepResult(
        signal_evaluation=signal_evaluation,
        decision_result=decision_result,
        broker_state=broker_state,
    )


def run_local_btc_futures_dry_run(
    request: RunLocalBtcFuturesDryRunRequest,
    *,
    clock: Clock | None = None,
    sleeper: Callable[[float], object] = time.sleep,
) -> RunLocalBtcFuturesDryRunResult:
    """Run a bounded local dry-run lifecycle without starting live market IO."""
    runtime = create_local_btc_futures_dry_run_runtime(
        request.config,
        clock=clock,
    )
    started = runtime.session.start()
    heartbeat = runtime.session.record_heartbeat(message="local dry-run runtime alive")
    deadline = time.monotonic() + request.duration_minutes * 60
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sleeper(min(request.heartbeat_seconds, remaining))
        heartbeat = runtime.session.record_heartbeat(message="local dry-run runtime alive")
    stopped = runtime.session.stop(message="bounded local dry-run complete")
    return RunLocalBtcFuturesDryRunResult(
        runtime=runtime,
        started_status=started,
        heartbeat=heartbeat,
        stopped_status=stopped,
    )


def _normalize_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        msg = f"{field_name} must be non-empty"
        raise ValidationError(msg)
    return normalized
