"""Compile domain market and signal inputs into compact simulation arrays."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.research.simulation.input import (
    SIGNAL_DIRECTION_LONG,
    SIGNAL_DIRECTION_SHORT,
    UNRESOLVED_BAR_INDEX,
    CompiledBarSeries,
    CompiledEntrySignals,
    CompiledSimulationInput,
)
from trading_framework.signal_model.definitions import SignalDirection


class CompileSimulationInputError(ValidationError):
    """Raised when simulation input cannot be compiled."""


def compile_simulation_input(
    *,
    bars: Sequence[MarketBar],
    entry_signals: pl.DataFrame,
) -> CompiledSimulationInput:
    """Materialize ordered bars and entry signals as contiguous NumPy arrays."""
    ordered_bars = tuple(bars)
    bar_series = _compile_bar_series(ordered_bars)
    signal_series = _compile_entry_signals(
        entry_signals=entry_signals,
        bar_series=bar_series,
    )
    return CompiledSimulationInput(bars=bar_series, entry_signals=signal_series)


def compile_simulation_input_from_columnar(
    *,
    column_batch: OhlcvColumnBatch,
    entry_signals: pl.DataFrame,
) -> CompiledSimulationInput:
    """Compile simulation arrays directly from columnar OHLCV without ``MarketBar`` objects."""
    bar_series = _compile_bar_series_from_columnar(column_batch)
    signal_series = _compile_entry_signals(
        entry_signals=entry_signals,
        bar_series=bar_series,
    )
    return CompiledSimulationInput(bars=bar_series, entry_signals=signal_series)


def resolve_signal_bar_index(
    *,
    observed_at_to_index: dict[int, int],
    available_at_to_index: dict[int, int],
    available_at_ns: int,
) -> int:
    """Resolve one signal to a bar index using observed_at then available_at."""
    observed_match = observed_at_to_index.get(available_at_ns)
    if observed_match is not None:
        return observed_match
    available_match = available_at_to_index.get(available_at_ns)
    if available_match is not None:
        return available_match
    return UNRESOLVED_BAR_INDEX


def datetime_to_epoch_ns(value: datetime) -> int:
    """Convert one UTC-aware datetime to epoch nanoseconds."""
    return int(value.timestamp() * 1_000_000_000)


def epoch_ns_to_datetime(value: int) -> datetime:
    """Convert epoch nanoseconds to one UTC-aware datetime."""
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC)


def _compile_bar_series(bars: Sequence[MarketBar]) -> CompiledBarSeries:
    bar_count = len(bars)
    if bar_count == 0:
        return CompiledBarSeries(
            observed_at_ns=np.empty(0, dtype=np.int64),
            available_at_ns=np.empty(0, dtype=np.int64),
            open_prices=np.empty(0, dtype=np.float64),
            high_prices=np.empty(0, dtype=np.float64),
            low_prices=np.empty(0, dtype=np.float64),
            close_prices=np.empty(0, dtype=np.float64),
            volume=np.empty(0, dtype=np.float64),
        )

    observed_at_ns = np.empty(bar_count, dtype=np.int64)
    available_at_ns = np.empty(bar_count, dtype=np.int64)
    open_prices = np.empty(bar_count, dtype=np.float64)
    high_prices = np.empty(bar_count, dtype=np.float64)
    low_prices = np.empty(bar_count, dtype=np.float64)
    close_prices = np.empty(bar_count, dtype=np.float64)
    volume = np.empty(bar_count, dtype=np.float64)

    for index, bar in enumerate(bars):
        observed_at_ns[index] = datetime_to_epoch_ns(bar.observed_at)
        available_at_ns[index] = datetime_to_epoch_ns(bar.available_at)
        open_prices[index] = float(bar.open.value)
        high_prices[index] = float(bar.high.value)
        low_prices[index] = float(bar.low.value)
        close_prices[index] = float(bar.close.value)
        volume[index] = float(bar.volume.value)

    return CompiledBarSeries(
        observed_at_ns=observed_at_ns,
        available_at_ns=available_at_ns,
        open_prices=open_prices,
        high_prices=high_prices,
        low_prices=low_prices,
        close_prices=close_prices,
        volume=volume,
    )


def _compile_bar_series_from_columnar(column_batch: OhlcvColumnBatch) -> CompiledBarSeries:
    bar_count = len(column_batch.timestamps)
    if bar_count == 0:
        return CompiledBarSeries(
            observed_at_ns=np.empty(0, dtype=np.int64),
            available_at_ns=np.empty(0, dtype=np.int64),
            open_prices=np.empty(0, dtype=np.float64),
            high_prices=np.empty(0, dtype=np.float64),
            low_prices=np.empty(0, dtype=np.float64),
            close_prices=np.empty(0, dtype=np.float64),
            volume=np.empty(0, dtype=np.float64),
        )

    observed_at_ns = np.fromiter(
        (datetime_to_epoch_ns(timestamp) for timestamp in column_batch.timestamps),
        dtype=np.int64,
        count=bar_count,
    )
    available_at_ns = np.fromiter(
        (datetime_to_epoch_ns(timestamp) for timestamp in column_batch.available_at),
        dtype=np.int64,
        count=bar_count,
    )
    return CompiledBarSeries(
        observed_at_ns=observed_at_ns,
        available_at_ns=available_at_ns,
        open_prices=np.asarray(column_batch.open, dtype=np.float64),
        high_prices=np.asarray(column_batch.high, dtype=np.float64),
        low_prices=np.asarray(column_batch.low, dtype=np.float64),
        close_prices=np.asarray(column_batch.close, dtype=np.float64),
        volume=np.asarray(column_batch.volume, dtype=np.float64),
    )


def _compile_entry_signals(
    *,
    entry_signals: pl.DataFrame,
    bar_series: CompiledBarSeries,
) -> CompiledEntrySignals:
    sorted_signals = entry_signals.sort("available_at")
    signal_count = len(sorted_signals)
    if signal_count == 0:
        return CompiledEntrySignals(
            available_at_ns=np.empty(0, dtype=np.int64),
            direction=np.empty(0, dtype=np.int8),
            signal_bar_index=np.empty(0, dtype=np.int32),
        )

    observed_at_to_index = _build_timestamp_index(bar_series.observed_at_ns)
    available_at_to_index = _build_timestamp_index(bar_series.available_at_ns)

    available_at_values = np.empty(signal_count, dtype=np.int64)
    direction_values = np.empty(signal_count, dtype=np.int8)
    signal_bar_index_values = np.empty(signal_count, dtype=np.int32)

    for index, row in enumerate(sorted_signals.iter_rows(named=True)):
        available_at = row["available_at"]
        if not isinstance(available_at, datetime):
            msg = "entry_signals.available_at must contain UTC-aware datetimes"
            raise CompileSimulationInputError(msg)
        available_at_ns = datetime_to_epoch_ns(available_at)
        available_at_values[index] = available_at_ns
        direction_values[index] = _encode_signal_direction(str(row["direction"]))
        signal_bar_index_values[index] = resolve_signal_bar_index(
            observed_at_to_index=observed_at_to_index,
            available_at_to_index=available_at_to_index,
            available_at_ns=available_at_ns,
        )

    return CompiledEntrySignals(
        available_at_ns=available_at_values,
        direction=direction_values,
        signal_bar_index=signal_bar_index_values,
    )


def _build_timestamp_index(timestamps_ns: np.ndarray) -> dict[int, int]:
    index_by_timestamp: dict[int, int] = {}
    for index, timestamp_ns in enumerate(timestamps_ns.tolist()):
        index_by_timestamp.setdefault(int(timestamp_ns), index)
    return index_by_timestamp


def _encode_signal_direction(direction: str) -> int:
    normalized = SignalDirection(direction)
    if normalized is SignalDirection.LONG:
        return SIGNAL_DIRECTION_LONG
    if normalized is SignalDirection.SHORT:
        return SIGNAL_DIRECTION_SHORT
    msg = f"unsupported entry signal direction: {direction}"
    raise CompileSimulationInputError(msg)
