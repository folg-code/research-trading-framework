"""Strategy Research simulation contracts."""

from trading_framework.research.simulation.assumptions import (
    FillPolicy,
    SimulationAssumptions,
    SimulationAssumptionsError,
    apply_entry_slippage,
    apply_exit_slippage,
    simulation_assumptions_fingerprint,
)

__all__ = [
    "FillPolicy",
    "SimulationAssumptions",
    "SimulationAssumptionsError",
    "apply_entry_slippage",
    "apply_exit_slippage",
    "simulation_assumptions_fingerprint",
]
