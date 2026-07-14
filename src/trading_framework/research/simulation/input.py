"""Compact NumPy input bundles for bar-sequential simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

SIGNAL_DIRECTION_LONG: int = 1
SIGNAL_DIRECTION_SHORT: int = -1
UNRESOLVED_BAR_INDEX: int = -1


@dataclass(frozen=True, slots=True)
class CompiledBarSeries:
    """Ordered OHLCV bars encoded as contiguous numeric arrays."""

    observed_at_ns: npt.NDArray[np.int64]
    available_at_ns: npt.NDArray[np.int64]
    open_prices: npt.NDArray[np.float64]
    high_prices: npt.NDArray[np.float64]
    low_prices: npt.NDArray[np.float64]
    close_prices: npt.NDArray[np.float64]
    volume: npt.NDArray[np.float64]

    @property
    def bar_count(self) -> int:
        return int(self.observed_at_ns.shape[0])


@dataclass(frozen=True, slots=True)
class CompiledEntrySignals:
    """Entry intents aligned to bar indices and sorted by availability time."""

    available_at_ns: npt.NDArray[np.int64]
    direction: npt.NDArray[np.int8]
    signal_bar_index: npt.NDArray[np.int32]


@dataclass(frozen=True, slots=True)
class CompiledSimulationInput:
    """Compiled market bars and entry signals ready for sequential simulation."""

    bars: CompiledBarSeries
    entry_signals: CompiledEntrySignals
