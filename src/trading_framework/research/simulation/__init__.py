"""Strategy Research simulation contracts."""

from trading_framework.research.simulation.assumptions import (
    FillPolicy,
    SimulationAssumptions,
    SimulationAssumptionsError,
    apply_entry_slippage,
    apply_exit_slippage,
    simulation_assumptions_fingerprint,
)
from trading_framework.research.simulation.engine import (
    BarSequentialSimulator,
    SimulationEngineError,
    SimulationResult,
)
from trading_framework.research.simulation.facts import (
    EquityPoint,
    SimulatedTrade,
    derive_trade_id,
    empty_equity_points_dataframe,
    empty_simulated_trades_dataframe,
    equity_points_to_dataframe,
    simulated_trades_to_dataframe,
)

__all__ = [
    "BarSequentialSimulator",
    "EquityPoint",
    "FillPolicy",
    "SimulatedTrade",
    "SimulationAssumptions",
    "SimulationAssumptionsError",
    "SimulationEngineError",
    "SimulationResult",
    "apply_entry_slippage",
    "apply_exit_slippage",
    "derive_trade_id",
    "empty_equity_points_dataframe",
    "empty_simulated_trades_dataframe",
    "equity_points_to_dataframe",
    "simulated_trades_to_dataframe",
    "simulation_assumptions_fingerprint",
]
