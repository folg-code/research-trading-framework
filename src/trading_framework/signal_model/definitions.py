"""Signal Model definitions."""

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.model_expression.expressions import Expression


class SignalDirection(StrEnum):
    """Explicit static direction assigned by the signal model definition."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class SignalFiringPolicy(StrEnum):
    """Policy converting dense condition results into sparse emissions."""

    ON_TRUE_EDGE = "on_true_edge"
    ON_EVENT = "on_event"


@dataclass(frozen=True, slots=True)
class SignalModelDefinition:
    """Declarative signal condition with explicit direction and firing policy."""

    signal_model_id: str
    expression: Expression
    direction: SignalDirection
    firing_policy: SignalFiringPolicy

    def __post_init__(self) -> None:
        normalized = self.signal_model_id.strip()
        if not normalized:
            msg = "signal_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.signal_model_id:
            object.__setattr__(self, "signal_model_id", normalized)
