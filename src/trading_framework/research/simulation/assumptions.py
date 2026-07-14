"""Simulation assumptions for bar-sequential Strategy Research."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.signal_model.definitions import SignalDirection


class SimulationAssumptionsError(ValidationError):
    """Raised when simulation assumptions are invalid or unsupported."""


class FillPolicy(StrEnum):
    """Explicit fill-price policy for simulated orders."""

    NEXT_BAR_OPEN = "next_bar_open"
    SAME_BAR_CLOSE = "same_bar_close"


_BPS_DIVISOR = Decimal("10000")


@dataclass(frozen=True, slots=True)
class SimulationAssumptions:
    """Binding execution assumptions included in Strategy Research run identity."""

    fill_policy_entry: FillPolicy = FillPolicy.NEXT_BAR_OPEN
    fill_policy_exit: FillPolicy = FillPolicy.NEXT_BAR_OPEN
    slippage_bps: Decimal = Decimal("0")
    commission_per_side: Decimal = Decimal("0")
    initial_capital: Decimal = Decimal("100000")

    def __post_init__(self) -> None:
        _validate_fill_policy(self.fill_policy_entry, field_name="fill_policy_entry")
        _validate_fill_policy(self.fill_policy_exit, field_name="fill_policy_exit")
        _validate_non_negative_decimal(self.slippage_bps, field_name="slippage_bps")
        _validate_non_negative_decimal(self.commission_per_side, field_name="commission_per_side")
        _validate_positive_decimal(self.initial_capital, field_name="initial_capital")


def simulation_assumptions_fingerprint(assumptions: SimulationAssumptions) -> str:
    """Stable fingerprint for simulation assumptions included in run identity."""
    payload = "|".join(
        [
            assumptions.fill_policy_entry.value,
            assumptions.fill_policy_exit.value,
            format(assumptions.slippage_bps, "f"),
            format(assumptions.commission_per_side, "f"),
            format(assumptions.initial_capital, "f"),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def apply_entry_slippage(
    *,
    price: Decimal,
    direction: SignalDirection | str,
    slippage_bps: Decimal,
) -> Decimal:
    """Adjust entry fill price to a worse price for the given direction."""
    signed_direction = _normalize_direction(direction)
    adjustment = _slippage_adjustment(price=price, slippage_bps=slippage_bps)
    if signed_direction is SignalDirection.LONG:
        return price + adjustment
    return price - adjustment


def apply_exit_slippage(
    *,
    price: Decimal,
    direction: SignalDirection | str,
    slippage_bps: Decimal,
) -> Decimal:
    """Adjust exit fill price to a worse price for the given direction."""
    signed_direction = _normalize_direction(direction)
    adjustment = _slippage_adjustment(price=price, slippage_bps=slippage_bps)
    if signed_direction is SignalDirection.LONG:
        return price - adjustment
    return price + adjustment


def _normalize_direction(direction: SignalDirection | str) -> SignalDirection:
    if isinstance(direction, SignalDirection):
        return direction
    return SignalDirection(str(direction))


def _slippage_adjustment(*, price: Decimal, slippage_bps: Decimal) -> Decimal:
    if slippage_bps == 0:
        return Decimal("0")
    return price * slippage_bps / _BPS_DIVISOR


def _validate_fill_policy(policy: FillPolicy, *, field_name: str) -> None:
    if policy is not FillPolicy.NEXT_BAR_OPEN:
        msg = f"{field_name} must be NEXT_BAR_OPEN in MVP"
        raise SimulationAssumptionsError(msg)


def _validate_non_negative_decimal(value: Decimal, *, field_name: str) -> None:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite() or decimal_value < 0:
        msg = f"{field_name} must be a non-negative finite decimal"
        raise SimulationAssumptionsError(msg)


def _validate_positive_decimal(value: Decimal, *, field_name: str) -> None:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite() or decimal_value <= 0:
        msg = f"{field_name} must be a positive finite decimal"
        raise SimulationAssumptionsError(msg)
