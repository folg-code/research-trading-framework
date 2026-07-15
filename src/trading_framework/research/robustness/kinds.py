"""Robustness experiment kind identifiers."""

from enum import StrEnum


class RobustnessExperimentKind(StrEnum):
    """Declared analysis kinds for one robustness experiment."""

    PARAMETER_SWEEP = "PARAMETER_SWEEP"
    WALK_FORWARD = "WALK_FORWARD"
    STRESS_TEST = "STRESS_TEST"
    MONTE_CARLO = "MONTE_CARLO"
    STATISTICAL_DIAGNOSTICS = "STATISTICAL_DIAGNOSTICS"
