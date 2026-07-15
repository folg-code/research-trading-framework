"""Local BTCUSDT futures dry-run runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution import (
    LocalExecutionRuntimeSession,
    PaperBroker,
    PaperBrokerState,
    RuntimeDecisionStep,
    StrategyModelOrderAdapter,
)
from trading_framework.infrastructure.storage.execution_events import JsonlExecutionEventSink
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
    initial_state: PaperBrokerState


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
    return LocalBtcFuturesDryRunRuntime(
        config=config,
        session=session,
        broker=broker,
        decision_step=decision_step,
        initial_state=broker.initial_state(runtime_clock.now()),
    )


def _normalize_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        msg = f"{field_name} must be non-empty"
        raise ValidationError(msg)
    return normalized
