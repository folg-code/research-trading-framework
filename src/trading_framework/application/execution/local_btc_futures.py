"""Local BTCUSDT futures dry-run runtime assembly."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution import (
    ExecutionReadModelQuery,
    ExecutionStateRepository,
    ExecutionStateWriter,
    LiveSignalEvaluation,
    LocalExecutionRuntimeSession,
    OrderSide,
    PaperBroker,
    PaperBrokerResult,
    PaperBrokerState,
    PositionSide,
    RecentFillView,
    RuntimeDecisionStep,
    RuntimeDecisionStepResult,
    RuntimeStatusSnapshot,
    StrategyModelLiveSignalEvaluator,
    StrategyModelOrderAdapter,
    closed_bar_close_reference_quote,
    resolve_live_closed_bar_window,
)
from trading_framework.execution.models import (
    ExecutionEvent,
    Heartbeat,
    PaperAccountSnapshot,
    PaperPosition,
)
from trading_framework.execution.protocols import ExecutionEventSink
from trading_framework.infrastructure.storage.execution_events import JsonlExecutionEventSink
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository
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
    state_repository_path: Path | None = None
    runtime_id: str = DEFAULT_LOCAL_BTC_FUTURES_RUNTIME_ID
    provider: str = DEFAULT_BINANCE_USDM_PROVIDER
    symbol: str = DEFAULT_BTCUSDT_SYMBOL
    account_id: str = DEFAULT_PAPER_ACCOUNT_ID
    currency: str = DEFAULT_PAPER_CURRENCY
    starting_equity: Decimal = DEFAULT_STARTING_EQUITY
    strategy_config: BtcFuturesDemoStrategyConfig | None = None
    restore_previous_state: bool = True

    def __post_init__(self) -> None:
        state_repository_path = self.state_repository_path or self.event_log_path.parent / "state"
        object.__setattr__(self, "state_repository_path", state_repository_path)
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
    signal_evaluator: StrategyModelLiveSignalEvaluator
    state_repository: ExecutionStateRepository
    initial_state: PaperBrokerState
    required_closed_bars: int
    max_closed_bars: int


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesClosedBarStepResult:
    """Result of one closed-bar local BTCUSDT dry-run step."""

    signal_evaluation: LiveSignalEvaluation
    decision_result: RuntimeDecisionStepResult
    broker_state: PaperBrokerState


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesClosedBarFeedStepResult:
    """Result of appending one closed bar to the local dry-run feed state."""

    closed_bars: tuple[MarketBar, ...]
    step_result: LocalBtcFuturesClosedBarStepResult


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
    state_repository: ExecutionStateRepository | None = None,
    max_closed_bars: int = 200,
) -> LocalBtcFuturesDryRunRuntime:
    """Assemble local dry-run runtime components without starting live IO."""
    runtime_clock = clock or SystemClock()
    state_repository_path = config.state_repository_path
    if state_repository_path is None:
        msg = "state_repository_path must be configured"
        raise ValidationError(msg)
    if max_closed_bars < 1:
        msg = "max_closed_bars must be positive"
        raise ValidationError(msg)
    repository = state_repository or JsonExecutionStateRepository(
        state_repository_path,
        clock=runtime_clock,
    )
    event_sink = _CompositeExecutionEventSink(
        (
            JsonlExecutionEventSink(config.event_log_path),
            _ExecutionStateEventSink(config.runtime_id, repository),
        )
    )
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
    signal_evaluator = StrategyModelLiveSignalEvaluator(strategy_model=strategy_model)
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
    initial_state = _restore_broker_state(
        broker=broker,
        repository=repository,
        config=config,
    )
    if initial_state is None:
        initial_state = broker.initial_state(runtime_clock.now())
    required_bars = signal_evaluator.required_closed_bars
    window = resolve_live_closed_bar_window(
        required_bars=required_bars,
        configured_cap=max_closed_bars,
    )
    return LocalBtcFuturesDryRunRuntime(
        config=config,
        session=session,
        broker=broker,
        decision_step=decision_step,
        signal_evaluator=signal_evaluator,
        state_repository=repository,
        initial_state=initial_state,
        required_closed_bars=required_bars,
        max_closed_bars=window,
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
    quote = closed_bar_close_reference_quote(
        symbol=runtime.config.symbol,
        bar=latest_bar,
    )
    broker_state_before_decision = runtime.broker.mark_to_market(
        latest_bar.close,
        latest_bar.available_at,
    )
    signal_evaluation = _evaluate_live_signals(
        runtime,
        closed_bars,
        broker_state_before_decision.position,
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
    _persist_latest_status(runtime)
    _persist_broker_state(runtime, broker_state)
    if decision_result.broker_result is not None:
        _persist_broker_result(runtime, decision_result.broker_result)
    return LocalBtcFuturesClosedBarStepResult(
        signal_evaluation=signal_evaluation,
        decision_result=decision_result,
        broker_state=broker_state,
    )


def run_local_btc_futures_closed_bar_feed_step(
    runtime: LocalBtcFuturesDryRunRuntime,
    *,
    closed_bars: tuple[MarketBar, ...],
    bar: MarketBar,
    max_closed_bars: int | None = None,
) -> LocalBtcFuturesClosedBarFeedStepResult:
    """Append one closed bar and run one deterministic local dry-run step."""
    window = max_closed_bars if max_closed_bars is not None else runtime.max_closed_bars
    if window < 1:
        msg = "max_closed_bars must be positive"
        raise ValidationError(msg)
    updated_bars = (*closed_bars, bar)[-window:]
    runtime.state_repository.save_bar(runtime.config.runtime_id, bar)
    step_result = run_local_btc_futures_closed_bar_step(runtime, updated_bars)
    return LocalBtcFuturesClosedBarFeedStepResult(
        closed_bars=updated_bars,
        step_result=step_result,
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
    _persist_status(runtime, started)
    _persist_broker_state(runtime, runtime.initial_state)
    heartbeat = runtime.session.record_heartbeat(message="local dry-run runtime alive")
    _persist_latest_status(runtime)
    deadline = time.monotonic() + request.duration_minutes * 60
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sleeper(min(request.heartbeat_seconds, remaining))
        heartbeat = runtime.session.record_heartbeat(message="local dry-run runtime alive")
        _persist_latest_status(runtime)
    stopped = runtime.session.stop(message="bounded local dry-run complete")
    _persist_status(runtime, stopped)
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


@final
@dataclass(frozen=True, slots=True)
class _CompositeExecutionEventSink:
    sinks: tuple[ExecutionEventSink, ...]

    def append(self, event: ExecutionEvent) -> None:
        for sink in self.sinks:
            sink.append(event)


@final
@dataclass(frozen=True, slots=True)
class _ExecutionStateEventSink:
    runtime_id: str
    repository: ExecutionStateWriter

    def append(self, event: ExecutionEvent) -> None:
        self.repository.append_event(self.runtime_id, event)


def _persist_status(
    runtime: LocalBtcFuturesDryRunRuntime,
    status: RuntimeStatusSnapshot,
) -> None:
    runtime.state_repository.save_runtime_status(status)


def _persist_latest_status(runtime: LocalBtcFuturesDryRunRuntime) -> None:
    status = runtime.session.latest_status(runtime.config.runtime_id)
    if status is not None:
        _persist_status(runtime, status)


def _persist_broker_state(
    runtime: LocalBtcFuturesDryRunRuntime,
    state: PaperBrokerState,
) -> None:
    runtime.state_repository.save_account(runtime.config.runtime_id, state.account)
    runtime.state_repository.save_position(runtime.config.runtime_id, state.position)


def _persist_broker_result(
    runtime: LocalBtcFuturesDryRunRuntime,
    result: PaperBrokerResult,
) -> None:
    runtime.state_repository.save_order(runtime.config.runtime_id, result.order)
    runtime.state_repository.save_fill(runtime.config.runtime_id, result.fill)


def _evaluate_live_signals(
    runtime: LocalBtcFuturesDryRunRuntime,
    closed_bars: tuple[MarketBar, ...],
    position: PaperPosition,
) -> LiveSignalEvaluation:
    evaluation = runtime.signal_evaluator.evaluate(closed_bars)
    exit_signal_active = evaluation.exit_signal_active or _fixed_bar_exit_active(
        runtime,
        closed_bars,
        position,
    )
    if exit_signal_active == evaluation.exit_signal_active:
        return evaluation
    return LiveSignalEvaluation(
        entry_signal_active=evaluation.entry_signal_active,
        exit_signal_active=exit_signal_active,
        condition_active=evaluation.condition_active,
        close=evaluation.close,
        ema_value=evaluation.ema_value,
    )


def _fixed_bar_exit_active(
    runtime: LocalBtcFuturesDryRunRuntime,
    closed_bars: tuple[MarketBar, ...],
    position: PaperPosition,
) -> bool:
    if position.side is not PositionSide.LONG:
        return False
    entry_fill = _latest_fill(runtime, side=OrderSide.BUY)
    if entry_fill is None:
        return False
    bars_after_entry = sum(1 for bar in closed_bars if bar.available_at > entry_fill.filled_at)
    exit_after_bars = runtime.signal_evaluator.strategy_model.exit_model.exit_bar_index(
        entry_fill_bar_index=0
    )
    return bars_after_entry >= exit_after_bars


def _latest_fill(
    runtime: LocalBtcFuturesDryRunRuntime,
    *,
    side: OrderSide,
) -> RecentFillView | None:
    view = runtime.state_repository.latest_status_view(
        ExecutionReadModelQuery(runtime_id=runtime.config.runtime_id)
    )
    if view is None:
        return None
    for fill in reversed(view.recent_fills):
        if fill.side is side:
            return fill
    return None


def _restore_broker_state(
    *,
    broker: PaperBroker,
    repository: ExecutionStateRepository,
    config: LocalBtcFuturesDryRunConfig,
) -> PaperBrokerState | None:
    if not config.restore_previous_state:
        return None
    view = repository.latest_status_view(ExecutionReadModelQuery(runtime_id=config.runtime_id))
    if (
        view is None
        or view.current_position is None
        or view.paper_equity is None
        or view.realized_pnl is None
        or view.unrealized_pnl is None
    ):
        return None
    account = PaperAccountSnapshot(
        account_id=config.account_id,
        currency=config.currency,
        starting_equity=config.starting_equity,
        realized_pnl=view.realized_pnl,
        unrealized_pnl=view.unrealized_pnl,
        equity=view.paper_equity,
        updated_at=view.current_position.updated_at,
    )
    return broker.restore_state(
        account=account,
        position=view.current_position,
        order_sequence=_last_numeric_suffix(
            (order.order_id for order in view.recent_orders),
            prefix="paper-order-",
        ),
        fill_sequence=_last_numeric_suffix(
            (fill.fill_id for fill in view.recent_fills),
            prefix="paper-fill-",
        ),
    )


def _last_numeric_suffix(values: Iterable[str], *, prefix: str) -> int:
    sequence = 0
    for value in values:
        text = str(value)
        if not text.startswith(prefix):
            continue
        suffix = text.removeprefix(prefix)
        if suffix.isdigit():
            sequence = max(sequence, int(suffix))
    return sequence
