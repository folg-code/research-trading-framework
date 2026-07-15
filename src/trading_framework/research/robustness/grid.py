"""Parameter grid expansion for robustness experiments."""

from __future__ import annotations

import itertools

from trading_framework.research.robustness.experiment import (
    ExperimentConfigCell,
    ParameterSweepSpec,
)
from trading_framework.research.robustness.fingerprint import (
    config_fingerprint,
    config_id_for_fingerprint,
)


def expand_parameter_grid(spec: ParameterSweepSpec) -> tuple[ExperimentConfigCell, ...]:
    """Expand a finite cartesian product over declared parameter axes."""
    axis_names = [axis.name for axis in spec.axes]
    axis_values = [axis.values for axis in spec.axes]
    cells: list[ExperimentConfigCell] = []
    for index, combination in enumerate(itertools.product(*axis_values)):
        overrides = dict(zip(axis_names, combination, strict=True))
        fingerprint = config_fingerprint(overrides)
        cells.append(
            ExperimentConfigCell(
                config_id=config_id_for_fingerprint(fingerprint, index=index),
                config_fingerprint=fingerprint,
                parameter_overrides=overrides,
            )
        )
    return tuple(cells)
