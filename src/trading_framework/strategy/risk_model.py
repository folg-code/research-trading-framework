"""Risk Model contracts for Strategy Research."""

from __future__ import annotations

from dataclasses import dataclass, field
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


def _as_decimal(value: Decimal | str | int | float) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True, slots=True)
class EquityPercentRiskModel:
    """STATIC, authoring-time equity-percent position sizing.

    The quantity is resolved exactly ONCE, in ``__post_init__``, from the
    values the author supplies at construction time::

        quantity = (account_equity * risk_percent) / stop_distance

    This lets an operator write "risk 1% of 100k on a 50-point stop"
    instead of hand-computing a lot size. It is deliberately **not**
    dynamic, compounding, or equity-curve-following sizing: the model has
    no access to running equity, fill prices, or trade-by-trade P&L, and
    ``position_quantity()`` always returns the one value derived at
    construction, for every entry, for the life of the run. This
    limitation must never be described as dynamic, compounding, or
    equity-curve-following sizing, here or anywhere else (see TD-026).

    v1 does NOT cross-validate ``stop_distance`` against a
    ``BracketExitModel``'s ``stop_loss_bps``: this risk model has no
    reference price with which to convert a basis-point offset into a
    price-point distance. The operator is responsible for keeping the two
    consistent; this is a deliberate v1 limitation, not an oversight
    (D-S048-05), and a cross-validation helper is a follow-on, not a v1
    promise.
    """

    account_equity: Decimal
    risk_percent: Decimal
    stop_distance: Decimal
    risk_model_id: str = "equity_percent"
    max_positions: int = 1
    quantity: Decimal = field(init=False)

    def __post_init__(self) -> None:
        normalized = self.risk_model_id.strip()
        if not normalized:
            msg = "risk_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.risk_model_id:
            object.__setattr__(self, "risk_model_id", normalized)

        account_equity = _as_decimal(self.account_equity)
        if account_equity != self.account_equity:
            object.__setattr__(self, "account_equity", account_equity)
        if account_equity <= 0:
            msg = "account_equity must be positive"
            raise ValidationError(msg)

        risk_percent = _as_decimal(self.risk_percent)
        if risk_percent != self.risk_percent:
            object.__setattr__(self, "risk_percent", risk_percent)
        if not (0 < risk_percent <= 1):
            msg = "risk_percent must be greater than 0 and at most 1"
            raise ValidationError(msg)

        stop_distance = _as_decimal(self.stop_distance)
        if stop_distance != self.stop_distance:
            object.__setattr__(self, "stop_distance", stop_distance)
        if stop_distance <= 0:
            msg = "stop_distance must be positive"
            raise ValidationError(msg)

        if self.max_positions < 1:
            msg = "max_positions must be at least 1"
            raise ValidationError(msg)

        # Resolved once, at authoring time, from the values above. Never
        # recomputed on later calls -- position_quantity() only returns
        # this stored value.
        derived_quantity = (account_equity * risk_percent) / stop_distance
        if derived_quantity <= 0:
            msg = "derived quantity must be positive"
            raise ValidationError(msg)
        object.__setattr__(self, "quantity", derived_quantity)

    def position_quantity(self) -> Decimal:
        return self.quantity

    def allows_new_entry(self, *, open_position_count: int) -> bool:
        if open_position_count < 0:
            msg = "open_position_count must be non-negative"
            raise ValidationError(msg)
        return open_position_count < self.max_positions
