"""Forward outcome definition — explicit semantics before calculation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.model_expression.references import MarketField
from trading_framework.strategy.reference_price import ReferencePricePolicy


class IncompleteHorizonPolicy(StrEnum):
    """How to handle occurrences whose forward window exceeds available bars."""

    EMIT_WITH_STATUS = "emit_with_status"


class OutcomeStatus(StrEnum):
    """Per-occurrence outcome row status."""

    COMPLETE = "complete"
    INCOMPLETE_HORIZON = "incomplete_horizon"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class ForwardOutcomeDefinition:
    """Binding forward-outcome semantics for one horizon."""

    horizon_bars: int
    reference_price_policy: ReferencePricePolicy = ReferencePricePolicy.CLOSE_AT_DETECTED_AT
    terminal_price_field: MarketField = MarketField.CLOSE
    excursion_high_field: MarketField = MarketField.HIGH
    excursion_low_field: MarketField = MarketField.LOW
    incomplete_horizon_policy: IncompleteHorizonPolicy = IncompleteHorizonPolicy.EMIT_WITH_STATUS

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            msg = "horizon_bars must be at least 1"
            raise ValidationError(msg)
