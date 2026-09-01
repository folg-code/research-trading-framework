"""Strategy Model composition contract."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.signal_model.definitions import SignalDirection, SignalModelDefinition
from trading_framework.strategy.exit_model import ExitModel
from trading_framework.strategy.risk_model import RiskModel


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


_EXIT_MODEL_MEMBERS: tuple[str, ...] = ("exit_model_id", "exit_bar_index")
_RISK_MODEL_MEMBERS: tuple[str, ...] = (
    "risk_model_id",
    "position_quantity",
    "allows_new_entry",
)


def validate_strategy_model_definition(definition: StrategyModelDefinition) -> None:
    """Reject unsupported or inconsistent strategy model combinations."""
    _require_dispatchable_exit_model(definition.exit_model)
    _require_structural_risk_model(definition.risk_model)
    if definition.signal_model.direction is SignalDirection.NEUTRAL:
        msg = "strategy signal_model must have a directional entry (long or short)"
        raise StrategyModelDefinitionError(msg)


def _require_dispatchable_exit_model(exit_model: object) -> None:
    """Accept any structurally conformant ``ExitModel``.

    The engine currently only *dispatches* ``FixedBarsExitModel`` to a kernel
    (research/simulation/engine.py); this check is deliberately wider than
    that, so a new exit model is not rejected here before the engine even
    sees it. A structurally conformant model that the engine cannot yet run
    is still rejected there, one layer down, not here.
    """
    if isinstance(exit_model, ExitModel):
        return
    missing = _missing_members(exit_model, _EXIT_MODEL_MEMBERS)
    msg = f"exit_model does not satisfy ExitModel: missing {missing}"
    raise StrategyModelDefinitionError(msg)


def _require_structural_risk_model(risk_model: object) -> None:
    """Accept any ``RiskModel`` exposing ``position_quantity`` + ``allows_new_entry``."""
    if isinstance(risk_model, RiskModel):
        return
    missing = _missing_members(risk_model, _RISK_MODEL_MEMBERS)
    msg = f"risk_model does not satisfy RiskModel: missing {missing}"
    raise StrategyModelDefinitionError(msg)


def _missing_members(candidate: object, member_names: Sequence[str]) -> list[str]:
    return [name for name in member_names if not hasattr(candidate, name)]
