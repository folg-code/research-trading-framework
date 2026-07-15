"""Robustness Research experiment contracts."""

from trading_framework.research.robustness.experiment import (
    ExperimentConfigCell,
    ParameterSweepAxis,
    ParameterSweepSpec,
    RobustnessExperimentSpec,
)
from trading_framework.research.robustness.grid import expand_parameter_grid
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.strategy_template import (
    CANONICAL_STRATEGY_TEMPLATE_ID,
    build_strategy_model_from_cell,
)

__all__ = [
    "CANONICAL_STRATEGY_TEMPLATE_ID",
    "ExperimentConfigCell",
    "ParameterSweepAxis",
    "ParameterSweepSpec",
    "RobustnessExperimentKind",
    "RobustnessExperimentSpec",
    "build_strategy_model_from_cell",
    "expand_parameter_grid",
]
