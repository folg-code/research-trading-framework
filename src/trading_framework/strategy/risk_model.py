"""Risk Model contracts for Strategy Research."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from trading_framework.core.exceptions import ValidationError


@runtime_checkable
class RiskModel(Protocol):
    """Contract for position sizing and exposure limits."""

    @property
    def risk_model_id(self) -> str:
        """Stable identifier for this risk model definition."""
        ...

    def position_quantity(self) -> Decimal:
        """Absolute position size for one entry."""
        ...

    def allows_new_entry(self, *, open_position_count: int) -> bool:
        """Whether another entry is permitted under current exposure."""
        ...


@dataclass(frozen=True, slots=True)
class FixedQuantityRiskModel:
    """Fixed absolute position size with a maximum open-position cap."""

    quantity: Decimal
    risk_model_id: str = "fixed_quantity"
    max_positions: int = 1

    def __post_init__(self) -> None:
        normalized = self.risk_model_id.strip()
        if not normalized:
            msg = "risk_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.risk_model_id:
            object.__setattr__(self, "risk_model_id", normalized)

        decimal_quantity = (
            self.quantity if isinstance(self.quantity, Decimal) else Decimal(str(self.quantity))
        )
        if decimal_quantity != self.quantity:
            object.__setattr__(self, "quantity", decimal_quantity)
        if decimal_quantity <= 0:
            msg = "quantity must be positive"
            raise ValidationError(msg)
        if self.max_positions < 1:
            msg = "max_positions must be at least 1"
            raise ValidationError(msg)

    def position_quantity(self) -> Decimal:
        return self.quantity

    def allows_new_entry(self, *, open_position_count: int) -> bool:
        if open_position_count < 0:
            msg = "open_position_count must be non-negative"
            raise ValidationError(msg)
        return open_position_count < self.max_positions
