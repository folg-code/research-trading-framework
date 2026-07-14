"""Strategy Research simulation contracts."""

from trading_framework.research.simulation.assumptions import (
    FillPolicy,
    SimulationAssumptions,
    SimulationAssumptionsError,
    apply_entry_slippage,
    apply_exit_slippage,
    simulation_assumptions_fingerprint,
)
from trading_framework.research.simulation.compile import (
    CompileSimulationInputError,
    compile_simulation_input,
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
from trading_framework.research.simulation.input import CompiledSimulationInput

__all__ = [
    "BarSequentialSimulator",
    "CompileSimulationInputError",
    "CompiledSimulationInput",
    "EquityPoint",
    "FillPolicy",
    "SimulatedTrade",
    "SimulationAssumptions",
    "SimulationAssumptionsError",
    "SimulationEngineError",
    "SimulationResult",
    "apply_entry_slippage",
    "apply_exit_slippage",
    "compile_simulation_input",
    "derive_trade_id",
    "empty_equity_points_dataframe",
    "empty_simulated_trades_dataframe",
    "equity_points_to_dataframe",
    "simulated_trades_to_dataframe",
    "simulation_assumptions_fingerprint",
]
