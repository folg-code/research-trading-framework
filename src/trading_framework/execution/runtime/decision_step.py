"""One-step dry-run runtime decision orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from trading_framework.execution.broker_sim import PaperBroker, PaperBrokerResult
from trading_framework.execution.models import BestBidAskSnapshot, PaperPosition
from trading_framework.execution.runtime.session import LocalExecutionRuntimeSession
from trading_framework.execution.runtime.strategy_orders import (
    StrategyModelOrderAdapter,
    StrategyOrderDecision,
)


@final
@dataclass(frozen=True, slots=True)
class RuntimeDecisionStepResult:
    """Outcome of one dry-run decision step."""

    decision: StrategyOrderDecision
    broker_result: PaperBrokerResult | None = None

    @property
    def order_submitted(self) -> bool:
        """Whether this step submitted a simulated order to the paper broker."""
        return self.broker_result is not None


@final
@dataclass(frozen=True, slots=True)
class RuntimeDecisionStep:
    """Apply one evaluated strategy decision against the paper broker."""

    session: LocalExecutionRuntimeSession
    strategy_adapter: StrategyModelOrderAdapter
    broker: PaperBroker

    def run(
        self,
        *,
        entry_signal_active: bool,
        exit_signal_active: bool,
        position: PaperPosition,
        quote: BestBidAskSnapshot,
    ) -> RuntimeDecisionStepResult:
        """Run one market-event decision step and emit lifecycle events."""
        current_signal = _current_signal_label(
            entry_signal_active=entry_signal_active,
            exit_signal_active=exit_signal_active,
        )
        self.session.record_market_event(
            event_at=quote.event_at,
            current_signal=current_signal,
        )
        decision = self.strategy_adapter.decide(
            entry_signal_active=entry_signal_active,
            exit_signal_active=exit_signal_active,
            position=position,
            requested_at=quote.event_at,
        )
        if decision.order_intent is None:
            return RuntimeDecisionStepResult(decision=decision)

        self.session.record_order_intent(decision.order_intent)
        broker_result = self.broker.accept_market_order(decision.order_intent, quote)
        self.session.record_broker_result(broker_result)
        return RuntimeDecisionStepResult(
            decision=decision,
            broker_result=broker_result,
        )


def _current_signal_label(*, entry_signal_active: bool, exit_signal_active: bool) -> str:
    if entry_signal_active and exit_signal_active:
        return "entry_and_exit_signal_active"
    if entry_signal_active:
        return "entry_signal_active"
    if exit_signal_active:
        return "exit_signal_active"
    return "no_signal"
