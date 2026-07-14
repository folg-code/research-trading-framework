"""Strategy Model composition contract."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.signal_model.definitions import SignalDirection, SignalModelDefinition
from trading_framework.strategy.exit_model import ExitModel, FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel, RiskModel


class StrategyModelDefinitionError(ValidationError):
    """Raised when a Strategy Model definition fails validation."""


@dataclass(frozen=True, slots=True)
class StrategyModelDefinition:
    """Composition of Market, Signal, Exit and Risk models for one strategy."""

    strategy_model_id: str
    market_model: MarketModelDefinition
    signal_model: SignalModelDefinition
    exit_model: ExitModel
    risk_model: RiskModel

    def __post_init__(self) -> None:
        normalized = self.strategy_model_id.strip()
        if not normalized:
            msg = "strategy_model_id must be non-empty"
            raise StrategyModelDefinitionError(msg)
        if normalized != self.strategy_model_id:
            object.__setattr__(self, "strategy_model_id", normalized)


def validate_strategy_model_definition(definition: StrategyModelDefinition) -> None:
    """Reject unsupported or inconsistent strategy model combinations."""
    if not isinstance(definition.exit_model, FixedBarsExitModel):
        msg = "MVP supports FixedBarsExitModel only"
        raise StrategyModelDefinitionError(msg)
    if not isinstance(definition.risk_model, FixedQuantityRiskModel):
        msg = "MVP supports FixedQuantityRiskModel only"
        raise StrategyModelDefinitionError(msg)
    if definition.signal_model.direction is SignalDirection.NEUTRAL:
        msg = "strategy signal_model must have a directional entry (long or short)"
        raise StrategyModelDefinitionError(msg)
