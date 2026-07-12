"""Market Model definitions."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.model_expression.expressions import Expression


@dataclass(frozen=True, slots=True)
class MarketModelDefinition:
    """Declarative market-context condition over Market Analysis outputs."""

    market_model_id: str
    expression: Expression

    def __post_init__(self) -> None:
        normalized = self.market_model_id.strip()
        if not normalized:
            msg = "market_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.market_model_id:
            object.__setattr__(self, "market_model_id", normalized)
