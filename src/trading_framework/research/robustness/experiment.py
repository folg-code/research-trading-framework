"""Robustness experiment specification contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.diagnostics import StatisticalDiagnosticsSpec
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.monte_carlo import MonteCarloSpec
from trading_framework.research.robustness.stress import StressTestSpec
from trading_framework.research.robustness.walk_forward import WalkForwardSpec

SUPPORTED_WAVE5_KINDS = frozenset(
    {
        RobustnessExperimentKind.PARAMETER_SWEEP,
        RobustnessExperimentKind.WALK_FORWARD,
        RobustnessExperimentKind.STRESS_TEST,
        RobustnessExperimentKind.MONTE_CARLO,
        RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS,
    }
)


@dataclass(frozen=True, slots=True)
class ParameterSweepAxis:
    """One swept parameter axis with explicit discrete values."""

    name: str
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not normalized_name:
            msg = "parameter axis name must be non-empty"
            raise ValidationError(msg)
        if not self.values:
            msg = f"parameter axis {normalized_name!r} requires at least one value"
            raise ValidationError(msg)
        object.__setattr__(self, "name", normalized_name)


@dataclass(frozen=True, slots=True)
class ParameterSweepSpec:
    """Finite cartesian grid over strategy template parameters."""

    axes: tuple[ParameterSweepAxis, ...]

    def __post_init__(self) -> None:
        if not self.axes:
            msg = "parameter sweep requires at least one axis"
            raise ValidationError(msg)
        names = [axis.name for axis in self.axes]
        if len(set(names)) != len(names):
            msg = "parameter sweep axis names must be unique"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class ExperimentConfigCell:
    """One concrete parameter assignment in a sweep grid."""

    config_id: str
    config_fingerprint: str
    parameter_overrides: dict[str, str]


@dataclass(frozen=True, slots=True)
class RobustnessExperimentSpec:
    """Declarative robustness experiment definition."""

    experiment_id: str
    kinds: tuple[RobustnessExperimentKind, ...]
    dataset_ref: str
    timeframe: str
    requested_range_start: datetime
    requested_range_end: datetime
    strategy_template_id: str
    parameter_sweep: ParameterSweepSpec | None = None
    walk_forward: WalkForwardSpec | None = None
    stress_test: StressTestSpec | None = None
    monte_carlo: MonteCarloSpec | None = None
    statistical_diagnostics: StatisticalDiagnosticsSpec | None = None
    evaluation_timeframe: str | None = None

    def __post_init__(self) -> None:
        normalized_id = self.experiment_id.strip()
        if not normalized_id:
            msg = "experiment_id must be non-empty"
            raise ValidationError(msg)
        object.__setattr__(self, "experiment_id", normalized_id)
        if not self.kinds:
            msg = "experiment requires at least one kind"
            raise ValidationError(msg)
        if self.requested_range_end < self.requested_range_start:
            msg = "requested_range_end must be >= requested_range_start"
            raise ValidationError(msg)
        validate_robustness_experiment_spec(self)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "kinds": [kind.value for kind in self.kinds],
            "dataset_ref": self.dataset_ref,
            "timeframe": self.timeframe,
            "requested_range_start": self.requested_range_start.isoformat(),
            "requested_range_end": self.requested_range_end.isoformat(),
            "strategy_template_id": self.strategy_template_id,
        }
        if self.evaluation_timeframe is not None:
            payload["evaluation_timeframe"] = self.evaluation_timeframe
        if self.parameter_sweep is not None:
            payload["parameter_sweep"] = {
                "axes": [
                    {"name": axis.name, "values": list(axis.values)}
                    for axis in self.parameter_sweep.axes
                ]
            }
        if self.walk_forward is not None:
            payload["walk_forward"] = self.walk_forward.to_dict()
        if self.stress_test is not None:
            payload["stress_test"] = self.stress_test.to_dict()
        if self.monte_carlo is not None:
            payload["monte_carlo"] = self.monte_carlo.to_dict()
        if self.statistical_diagnostics is not None:
            payload["statistical_diagnostics"] = self.statistical_diagnostics.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RobustnessExperimentSpec:
        sweep_payload = payload.get("parameter_sweep")
        parameter_sweep = None
        if sweep_payload is not None:
            axes = tuple(
                ParameterSweepAxis(
                    name=str(axis["name"]),
                    values=tuple(str(value) for value in axis["values"]),
                )
                for axis in sweep_payload["axes"]
            )
            parameter_sweep = ParameterSweepSpec(axes=axes)
        walk_forward_payload = payload.get("walk_forward")
        walk_forward = (
            WalkForwardSpec.from_dict(walk_forward_payload)
            if walk_forward_payload is not None
            else None
        )
        stress_payload = payload.get("stress_test")
        stress_test = (
            StressTestSpec.from_dict(stress_payload) if stress_payload is not None else None
        )
        monte_carlo_payload = payload.get("monte_carlo")
        monte_carlo = (
            MonteCarloSpec.from_dict(monte_carlo_payload)
            if monte_carlo_payload is not None
            else None
        )
        diagnostics_payload = payload.get("statistical_diagnostics")
        statistical_diagnostics = (
            StatisticalDiagnosticsSpec.from_dict(diagnostics_payload)
            if diagnostics_payload is not None
            else None
        )
        return cls(
            experiment_id=str(payload["experiment_id"]),
            kinds=tuple(RobustnessExperimentKind(kind) for kind in payload["kinds"]),
            dataset_ref=str(payload["dataset_ref"]),
            timeframe=str(payload["timeframe"]),
            requested_range_start=datetime.fromisoformat(str(payload["requested_range_start"])),
            requested_range_end=datetime.fromisoformat(str(payload["requested_range_end"])),
            strategy_template_id=str(payload["strategy_template_id"]),
            parameter_sweep=parameter_sweep,
            walk_forward=walk_forward,
            stress_test=stress_test,
            monte_carlo=monte_carlo,
            statistical_diagnostics=statistical_diagnostics,
            evaluation_timeframe=(
                str(payload["evaluation_timeframe"])
                if payload.get("evaluation_timeframe") is not None
                else None
            ),
        )


def validate_robustness_experiment_spec(spec: RobustnessExperimentSpec) -> None:
    """Validate wave-5-supported experiment declarations."""
    unsupported = [kind for kind in spec.kinds if kind not in SUPPORTED_WAVE5_KINDS]
    if unsupported:
        names = ", ".join(kind.value for kind in unsupported)
        msg = f"unsupported experiment kinds: {names}"
        raise ValidationError(msg)
    if RobustnessExperimentKind.PARAMETER_SWEEP in spec.kinds and spec.parameter_sweep is None:
        msg = "PARAMETER_SWEEP requires parameter_sweep"
        raise ValidationError(msg)
    if RobustnessExperimentKind.WALK_FORWARD in spec.kinds:
        if spec.walk_forward is None:
            msg = "WALK_FORWARD requires walk_forward"
            raise ValidationError(msg)
        if spec.parameter_sweep is None:
            msg = "WALK_FORWARD requires parameter_sweep for train selection"
            raise ValidationError(msg)
    if RobustnessExperimentKind.STRESS_TEST in spec.kinds and spec.stress_test is None:
        msg = "STRESS_TEST requires stress_test"
        raise ValidationError(msg)
    if RobustnessExperimentKind.MONTE_CARLO in spec.kinds and spec.monte_carlo is None:
        msg = "MONTE_CARLO requires monte_carlo"
        raise ValidationError(msg)
    if (
        RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS in spec.kinds
        and spec.statistical_diagnostics is None
    ):
        msg = "STATISTICAL_DIAGNOSTICS requires statistical_diagnostics"
        raise ValidationError(msg)
