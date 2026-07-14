"""Unit tests for Strategy Research simulation assumptions."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.research.simulation import (
    FillPolicy,
    SimulationAssumptions,
    SimulationAssumptionsError,
    apply_entry_slippage,
    apply_exit_slippage,
    simulation_assumptions_fingerprint,
)
from trading_framework.signal_model.definitions import SignalDirection


def test_simulation_assumptions_default_fingerprint_is_stable() -> None:
    assumptions = SimulationAssumptions()
    assert simulation_assumptions_fingerprint(assumptions) == "1aa6ee647c5cc636"


def test_simulation_assumptions_reject_negative_slippage() -> None:
    with pytest.raises(SimulationAssumptionsError, match="slippage_bps"):
        SimulationAssumptions(slippage_bps=Decimal("-1"))


def test_apply_entry_slippage_worsens_long_and_short_prices() -> None:
    price = Decimal("100")
    long_entry = apply_entry_slippage(
        price=price,
        direction=SignalDirection.LONG,
        slippage_bps=Decimal("10"),
    )
    short_entry = apply_entry_slippage(
        price=price,
        direction=SignalDirection.SHORT,
        slippage_bps=Decimal("10"),
    )
    assert long_entry > price
    assert short_entry < price


def test_apply_exit_slippage_worsens_long_and_short_prices() -> None:
    price = Decimal("100")
    long_exit = apply_exit_slippage(
        price=price,
        direction=SignalDirection.LONG,
        slippage_bps=Decimal("10"),
    )
    short_exit = apply_exit_slippage(
        price=price,
        direction=SignalDirection.SHORT,
        slippage_bps=Decimal("10"),
    )
    assert long_exit < price
    assert short_exit > price


def test_fill_policy_mvp_rejects_deferred_values() -> None:
    with pytest.raises(SimulationAssumptionsError, match="fill_policy_entry"):
        SimulationAssumptions(fill_policy_entry=FillPolicy.SAME_BAR_CLOSE)
