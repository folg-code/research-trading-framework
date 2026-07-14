"""Numba simulation kernels for Strategy Research."""

from trading_framework.research.simulation.kernels.fixed_bars import (
    FixedBarsKernelResult,
    materialize_kernel_equity,
    materialize_kernel_trades,
    run_fixed_bars_kernel,
)

__all__ = [
    "FixedBarsKernelResult",
    "materialize_kernel_equity",
    "materialize_kernel_trades",
    "run_fixed_bars_kernel",
]
