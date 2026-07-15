"""Translate Strategy Models into dry-run order intents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.models import (
    OrderIntent,
    OrderSide,
    OrderType,
    PaperPosition,
    PositionSide,
)
from trading_framework.signal_model import SignalDirection
from trading_framework.strategy import StrategyModelDefinition, validate_strategy_model_definition
from trading_framework.time.models.utc_instant import require_utc_aware

SIMULATED_DRY_RUN_REASON = "simulated dry-run order intent"


class StrategyOrderDecisionType(StrEnum):
    """Order decision emitted by a Strategy Model execution adapter."""

    HOLD = "hold"
    ENTER_LONG = "enter_long"
    FLATTEN_LONG = "flatten_long"


@final
@dataclass(frozen=True, slots=True)
class StrategyOrderDecision:
    """Decision emitted after adapting a Strategy Model to runtime state."""

    decision_type: StrategyOrderDecisionType
    reason: str
    order_intent: OrderIntent | None = None


@final
@dataclass(frozen=True, slots=True)
class StrategyModelOrderAdapter:
    """Create dry-run order intents from a shared Strategy Model definition."""

    strategy_model: StrategyModelDefinition
    symbol: str
    disclosure: str | None = None

    def __post_init__(self) -> None:
        validate_strategy_model_definition(self.strategy_model)
        if self.strategy_model.signal_model.direction is not SignalDirection.LONG:
            msg = "dry-run adapter supports long-only Strategy Models"
            raise ValidationError(msg)
        symbol = self.symbol.strip().upper()
        if not symbol:
            msg = "symbol must be non-empty"
            raise ValidationError(msg)
        object.__setattr__(self, "symbol", symbol)
        if self.disclosure is not None:
            disclosure = self.disclosure.strip()
            if not disclosure:
                msg = "disclosure must be non-empty when provided"
                raise ValidationError(msg)
            object.__setattr__(self, "disclosure", disclosure)

    def decide(
        self,
        *,
        entry_signal_active: bool,
        exit_signal_active: bool,
        position: PaperPosition,
        requested_at: datetime,
    ) -> StrategyOrderDecision:
        """Create a market-order intent when the model and runtime state require it."""
        timestamp = require_utc_aware(requested_at)
        if position.symbol != self.symbol:
            msg = "position symbol must match adapter symbol"
            raise ValidationError(msg)
        if position.side is PositionSide.FLAT:
            if entry_signal_active and self.strategy_model.risk_model.allows_new_entry(
                open_position_count=0
            ):
                return self._order_decision(
                    decision_type=StrategyOrderDecisionType.ENTER_LONG,
                    side=OrderSide.BUY,
                    quantity=self.strategy_model.risk_model.position_quantity(),
                    requested_at=timestamp,
                    reason="entry_signal_active",
                )
            return StrategyOrderDecision(
                decision_type=StrategyOrderDecisionType.HOLD,
                reason="flat_without_entry_signal",
            )
        if position.side is PositionSide.LONG:
            if exit_signal_active:
                return self._order_decision(
                    decision_type=StrategyOrderDecisionType.FLATTEN_LONG,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    requested_at=timestamp,
                    reason="exit_signal_active",
                )
            return StrategyOrderDecision(
                decision_type=StrategyOrderDecisionType.HOLD,
                reason="long_without_exit_signal",
            )
        return StrategyOrderDecision(
            decision_type=StrategyOrderDecisionType.HOLD,
            reason="unsupported_position_side",
        )

    def _order_decision(
        self,
        *,
        decision_type: StrategyOrderDecisionType,
        side: OrderSide,
        quantity: Decimal,
        requested_at: datetime,
        reason: str,
    ) -> StrategyOrderDecision:
        intent_reason = self._intent_reason(reason)
        intent_id = (
            f"{self.strategy_model.strategy_model_id}-"
            f"{requested_at.isoformat()}-{decision_type.value}-{side.value}"
        )
        return StrategyOrderDecision(
            decision_type=decision_type,
            reason=reason,
            order_intent=OrderIntent(
                intent_id=intent_id,
                strategy_id=self.strategy_model.strategy_model_id,
                symbol=self.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                requested_at=requested_at,
                reason=intent_reason,
            ),
        )

    def _intent_reason(self, reason: str) -> str:
        parts = [reason, SIMULATED_DRY_RUN_REASON]
        if self.disclosure is not None:
            parts.append(self.disclosure)
        return "; ".join(parts)
