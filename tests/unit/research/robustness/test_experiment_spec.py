"""Unit tests for robustness experiment specification validation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.diagnostics import StatisticalDiagnosticsSpec
from trading_framework.research.robustness.experiment import (
    ParameterSweepAxis,
    ParameterSweepSpec,
    RobustnessExperimentSpec,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.monte_carlo import MonteCarloSpec
from trading_framework.research.robustness.stress import (
    StressScenarioSpec,
    StressTestSpec,
)
from trading_framework.research.robustness.walk_forward import (
    WalkForwardSpec,
    WalkForwardWindowMode,
)
from trading_framework.strategy.canonical_examples import CANONICAL_STRATEGY_MODEL_ID

_DEFAULT_PARAMETER_SWEEP = ParameterSweepSpec(
    axes=(ParameterSweepAxis(name="exit_after_bars", values=("5", "10")),)
)
_DEFAULT_WALK_FORWARD = WalkForwardSpec(
    window_mode=WalkForwardWindowMode.ROLLING,
    train_duration_seconds=3600,
    oos_duration_seconds=1800,
    step_duration_seconds=1800,
)
_DEFAULT_STRESS_TEST = StressTestSpec(
    scenarios=(
        StressScenarioSpec(
            scenario_id="double_commission",
            commission_multiplier=Decimal("2"),
        ),
    ),
)
_DEFAULT_MONTE_CARLO = MonteCarloSpec(path_count=10, rng_seed=1)
_DEFAULT_DIAGNOSTICS = StatisticalDiagnosticsSpec()


def _base_spec(
    *,
    experiment_id: str = "exp-test-001",
    kinds: tuple[RobustnessExperimentKind, ...] = (RobustnessExperimentKind.PARAMETER_SWEEP,),
    parameter_sweep: ParameterSweepSpec | None = _DEFAULT_PARAMETER_SWEEP,
    walk_forward: WalkForwardSpec | None = None,
    stress_test: StressTestSpec | None = None,
    monte_carlo: MonteCarloSpec | None = None,
    statistical_diagnostics: StatisticalDiagnosticsSpec | None = None,
) -> RobustnessExperimentSpec:
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=kinds,
        dataset_ref="ES.c.0/ohlcv/1m/csv/unit",
        timeframe="1m",
        requested_range_start=datetime(2024, 6, 3, 14, 30, tzinfo=UTC),
        requested_range_end=datetime(2024, 6, 3, 20, 0, tzinfo=UTC),
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        parameter_sweep=parameter_sweep,
        walk_forward=walk_forward,
        stress_test=stress_test,
        monte_carlo=monte_carlo,
        statistical_diagnostics=statistical_diagnostics,
    )


def test_robustness_experiment_spec_roundtrip_dict() -> None:
    spec = _base_spec()
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_robustness_experiment_spec_requires_monte_carlo_block() -> None:
    with pytest.raises(ValidationError, match="requires monte_carlo"):
        _base_spec(
            kinds=(RobustnessExperimentKind.MONTE_CARLO,),
            parameter_sweep=None,
            monte_carlo=None,
        )


def test_robustness_experiment_spec_requires_diagnostics_block() -> None:
    with pytest.raises(ValidationError, match="requires statistical_diagnostics"):
        _base_spec(
            kinds=(RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS,),
            parameter_sweep=None,
            statistical_diagnostics=None,
        )


def test_robustness_experiment_spec_requires_walk_forward_block() -> None:
    with pytest.raises(ValidationError, match="requires walk_forward"):
        _base_spec(
            kinds=(RobustnessExperimentKind.WALK_FORWARD,),
            parameter_sweep=_DEFAULT_PARAMETER_SWEEP,
            walk_forward=None,
        )


def test_robustness_experiment_spec_walk_forward_roundtrip_dict() -> None:
    spec = _base_spec(
        kinds=(RobustnessExperimentKind.WALK_FORWARD,),
        walk_forward=_DEFAULT_WALK_FORWARD,
    )
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_robustness_experiment_spec_requires_parameter_sweep_block() -> None:
    with pytest.raises(ValidationError, match="requires parameter_sweep"):
        _base_spec(parameter_sweep=None)


def test_robustness_experiment_spec_requires_stress_test_block() -> None:
    with pytest.raises(ValidationError, match="requires stress_test"):
        _base_spec(
            kinds=(RobustnessExperimentKind.STRESS_TEST,),
            parameter_sweep=None,
            stress_test=None,
        )


def test_robustness_experiment_spec_stress_roundtrip_dict() -> None:
    spec = _base_spec(
        kinds=(RobustnessExperimentKind.STRESS_TEST,),
        parameter_sweep=None,
        stress_test=_DEFAULT_STRESS_TEST,
    )
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_robustness_experiment_spec_monte_carlo_roundtrip_dict() -> None:
    spec = _base_spec(
        kinds=(RobustnessExperimentKind.MONTE_CARLO,),
        parameter_sweep=None,
        monte_carlo=_DEFAULT_MONTE_CARLO,
    )
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_robustness_experiment_spec_diagnostics_roundtrip_dict() -> None:
    spec = _base_spec(
        kinds=(RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS,),
        parameter_sweep=None,
        statistical_diagnostics=_DEFAULT_DIAGNOSTICS,
    )
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec
