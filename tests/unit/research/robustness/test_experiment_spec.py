"""Unit tests for robustness experiment specification validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.experiment import (
    ParameterSweepAxis,
    ParameterSweepSpec,
    RobustnessExperimentSpec,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
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


def _base_spec(
    *,
    experiment_id: str = "exp-test-001",
    kinds: tuple[RobustnessExperimentKind, ...] = (RobustnessExperimentKind.PARAMETER_SWEEP,),
    parameter_sweep: ParameterSweepSpec | None = _DEFAULT_PARAMETER_SWEEP,
    walk_forward: WalkForwardSpec | None = None,
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
    )


def test_robustness_experiment_spec_roundtrip_dict() -> None:
    spec = _base_spec()
    restored = RobustnessExperimentSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_robustness_experiment_spec_rejects_unsupported_kind() -> None:
    with pytest.raises(ValidationError, match="unsupported experiment kinds"):
        _base_spec(kinds=(RobustnessExperimentKind.MONTE_CARLO,))


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
