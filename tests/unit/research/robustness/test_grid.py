"""Unit tests for robustness parameter grid expansion."""

from __future__ import annotations

from trading_framework.research.robustness.experiment import (
    ParameterSweepAxis,
    ParameterSweepSpec,
)
from trading_framework.research.robustness.grid import expand_parameter_grid


def test_expand_parameter_grid_cartesian_product() -> None:
    spec = ParameterSweepSpec(
        axes=(
            ParameterSweepAxis(name="exit_after_bars", values=("5", "10")),
            ParameterSweepAxis(name="volatility_period", values=("14", "20")),
        )
    )

    cells = expand_parameter_grid(spec)

    assert len(cells) == 4
    overrides = [cell.parameter_overrides for cell in cells]
    assert {"exit_after_bars": "5", "volatility_period": "14"} in overrides
    assert {"exit_after_bars": "10", "volatility_period": "20"} in overrides
    config_ids = {cell.config_id for cell in cells}
    assert len(config_ids) == 4
    fingerprints = {cell.config_fingerprint for cell in cells}
    assert len(fingerprints) == 4
