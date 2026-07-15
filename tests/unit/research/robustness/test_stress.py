"""Unit tests for stress scenario contracts and transforms."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.stress import (
    StressScenarioMode,
    StressScenarioSpec,
    StressTestSpec,
    apply_stress_assumptions,
    apply_stress_strategy_model,
    scenario_fingerprint,
    validate_stress_scenario_spec,
)
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy.canonical_examples import build_canonical_strategy_model
from trading_framework.strategy.exit_model import FixedBarsExitModel


def test_stress_scenario_spec_roundtrip_dict() -> None:
    scenario = StressScenarioSpec(
        scenario_id="double_slippage",
        slippage_multiplier=Decimal("2"),
    )
    restored = StressScenarioSpec.from_dict(scenario.to_dict())
    assert restored == scenario
    assert scenario.mode() is StressScenarioMode.RERUN


def test_stress_scenario_spec_post_process_mode() -> None:
    scenario = StressScenarioSpec(
        scenario_id="remove_top",
        remove_top_n_trades=2,
    )
    assert scenario.mode() is StressScenarioMode.POST_PROCESS


def test_validate_stress_scenario_rejects_empty_mechanism() -> None:
    with pytest.raises(ValidationError, match="at least one stress dimension"):
        validate_stress_scenario_spec(
            StressScenarioSpec(scenario_id="empty"),
        )


def test_validate_stress_scenario_rejects_mixed_modes() -> None:
    with pytest.raises(ValidationError, match="cannot combine rerun and post-process"):
        validate_stress_scenario_spec(
            StressScenarioSpec(
                scenario_id="mixed",
                commission_multiplier=Decimal("2"),
                remove_top_n_trades=1,
            ),
        )


def test_scenario_fingerprint_is_stable() -> None:
    scenario = StressScenarioSpec(
        scenario_id="delay",
        entry_delay_bars=1,
        exit_delay_bars=2,
    )
    assert scenario_fingerprint(scenario) == scenario_fingerprint(scenario)


def test_apply_stress_assumptions_scales_costs() -> None:
    baseline = SimulationAssumptions(
        slippage_bps=Decimal("10"),
        commission_per_side=Decimal("2.5"),
    )
    scenario = StressScenarioSpec(
        scenario_id="costs",
        commission_multiplier=Decimal("2"),
        slippage_multiplier=Decimal("3"),
    )
    stressed = apply_stress_assumptions(baseline, scenario)
    assert stressed.slippage_bps == Decimal("30")
    assert stressed.commission_per_side == Decimal("5")


def test_apply_stress_strategy_model_adds_delay_bars() -> None:
    strategy = build_canonical_strategy_model(exit_after_bars=5)
    scenario = StressScenarioSpec(
        scenario_id="delay",
        entry_delay_bars=1,
        exit_delay_bars=2,
    )
    stressed = apply_stress_strategy_model(strategy, scenario)
    exit_model = stressed.exit_model
    assert isinstance(exit_model, FixedBarsExitModel)
    assert exit_model.exit_after_bars == 8


def test_stress_test_spec_requires_unique_scenario_ids() -> None:
    scenario = StressScenarioSpec(
        scenario_id="dup",
        commission_multiplier=Decimal("2"),
    )
    with pytest.raises(ValidationError, match="unique"):
        StressTestSpec(scenarios=(scenario, scenario))
