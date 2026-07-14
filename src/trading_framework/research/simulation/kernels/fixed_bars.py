"""Numba kernel for FixedBarsExitModel bar-sequential simulation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import numpy.typing as npt
from numba import njit

from trading_framework.research.simulation.compile import epoch_ns_to_datetime
from trading_framework.research.simulation.facts import EquityPoint, SimulatedTrade, derive_trade_id
from trading_framework.research.simulation.input import (
    SIGNAL_DIRECTION_LONG,
    UNRESOLVED_BAR_INDEX,
    CompiledSimulationInput,
)
from trading_framework.signal_model.definitions import SignalDirection
from trading_framework.strategy.exit_model import ExitReason

_BPS_DIVISOR = 10_000.0


@dataclass(frozen=True, slots=True)
class FixedBarsKernelResult:
    """Numeric simulation output buffers materialized after kernel execution."""

    trade_count: int
    entry_signal_at_ns: npt.NDArray[np.int64]
    entry_fill_at_ns: npt.NDArray[np.int64]
    exit_signal_at_ns: npt.NDArray[np.int64]
    exit_fill_at_ns: npt.NDArray[np.int64]
    entry_fill_price: npt.NDArray[np.float64]
    exit_fill_price: npt.NDArray[np.float64]
    gross_pnl: npt.NDArray[np.float64]
    commission_paid: npt.NDArray[np.float64]
    net_pnl: npt.NDArray[np.float64]
    bars_held: npt.NDArray[np.int32]
    direction: npt.NDArray[np.int8]
    equity: npt.NDArray[np.float64]
    drawdown: npt.NDArray[np.float64]
    open_position_count: npt.NDArray[np.int32]


def run_fixed_bars_kernel(
    compiled: CompiledSimulationInput,
    *,
    exit_after_bars: int,
    quantity: float,
    slippage_bps: float,
    commission_per_side: float,
    initial_capital: float,
) -> FixedBarsKernelResult:
    """Execute the fixed-bars Numba kernel on one compiled simulation input."""
    bar_series = compiled.bars
    signal_series = compiled.entry_signals
    bar_count = bar_series.bar_count
    signal_count = int(signal_series.available_at_ns.shape[0])
    max_trades = max(signal_count, 1)

    result = FixedBarsKernelResult(
        trade_count=0,
        entry_signal_at_ns=np.empty(max_trades, dtype=np.int64),
        entry_fill_at_ns=np.empty(max_trades, dtype=np.int64),
        exit_signal_at_ns=np.empty(max_trades, dtype=np.int64),
        exit_fill_at_ns=np.empty(max_trades, dtype=np.int64),
        entry_fill_price=np.empty(max_trades, dtype=np.float64),
        exit_fill_price=np.empty(max_trades, dtype=np.float64),
        gross_pnl=np.empty(max_trades, dtype=np.float64),
        commission_paid=np.empty(max_trades, dtype=np.float64),
        net_pnl=np.empty(max_trades, dtype=np.float64),
        bars_held=np.empty(max_trades, dtype=np.int32),
        direction=np.empty(max_trades, dtype=np.int8),
        equity=np.empty(bar_count, dtype=np.float64),
        drawdown=np.empty(bar_count, dtype=np.float64),
        open_position_count=np.empty(bar_count, dtype=np.int32),
    )
    if bar_count == 0:
        return result

    trade_count = simulate_fixed_bars_exit_kernel(
        bar_series.observed_at_ns,
        bar_series.open_prices,
        signal_series.available_at_ns,
        signal_series.direction,
        signal_series.signal_bar_index,
        exit_after_bars,
        quantity,
        slippage_bps,
        commission_per_side,
        initial_capital,
        result.entry_signal_at_ns,
        result.entry_fill_at_ns,
        result.exit_signal_at_ns,
        result.exit_fill_at_ns,
        result.entry_fill_price,
        result.exit_fill_price,
        result.gross_pnl,
        result.commission_paid,
        result.net_pnl,
        result.bars_held,
        result.direction,
        result.equity,
        result.drawdown,
        result.open_position_count,
    )
    return FixedBarsKernelResult(
        trade_count=trade_count,
        entry_signal_at_ns=result.entry_signal_at_ns[:trade_count],
        entry_fill_at_ns=result.entry_fill_at_ns[:trade_count],
        exit_signal_at_ns=result.exit_signal_at_ns[:trade_count],
        exit_fill_at_ns=result.exit_fill_at_ns[:trade_count],
        entry_fill_price=result.entry_fill_price[:trade_count],
        exit_fill_price=result.exit_fill_price[:trade_count],
        gross_pnl=result.gross_pnl[:trade_count],
        commission_paid=result.commission_paid[:trade_count],
        net_pnl=result.net_pnl[:trade_count],
        bars_held=result.bars_held[:trade_count],
        direction=result.direction[:trade_count],
        equity=result.equity,
        drawdown=result.drawdown,
        open_position_count=result.open_position_count,
    )


def materialize_kernel_trades(
    result: FixedBarsKernelResult,
    *,
    strategy_model_id: str,
    instrument: str,
    source_dataset_ref: str,
    exit_reason: ExitReason,
    quantity: Decimal,
) -> list[SimulatedTrade]:
    """Convert kernel trade buffers into domain facts."""
    trades: list[SimulatedTrade] = []
    for index in range(result.trade_count):
        direction_code = int(result.direction[index])
        direction = (
            SignalDirection.LONG
            if direction_code == SIGNAL_DIRECTION_LONG
            else SignalDirection.SHORT
        )
        entry_signal_at = epoch_ns_to_datetime(int(result.entry_signal_at_ns[index]))
        trades.append(
            SimulatedTrade(
                trade_id=derive_trade_id(
                    strategy_model_id=strategy_model_id,
                    entry_signal_at=entry_signal_at,
                    direction=direction.value,
                ),
                strategy_model_id=strategy_model_id,
                instrument=instrument,
                direction=direction.value,
                entry_signal_at=entry_signal_at,
                entry_fill_at=epoch_ns_to_datetime(int(result.entry_fill_at_ns[index])),
                entry_fill_price=_decimal_from_float(float(result.entry_fill_price[index])),
                exit_signal_at=epoch_ns_to_datetime(int(result.exit_signal_at_ns[index])),
                exit_fill_at=epoch_ns_to_datetime(int(result.exit_fill_at_ns[index])),
                exit_fill_price=_decimal_from_float(float(result.exit_fill_price[index])),
                quantity=quantity,
                gross_pnl=_decimal_from_float(float(result.gross_pnl[index])),
                commission_paid=_decimal_from_float(float(result.commission_paid[index])),
                net_pnl=_decimal_from_float(float(result.net_pnl[index])),
                bars_held=int(result.bars_held[index]),
                exit_reason=exit_reason,
                source_dataset_ref=source_dataset_ref,
            )
        )
    return trades


def materialize_kernel_equity(
    result: FixedBarsKernelResult,
    observed_at_ns: npt.NDArray[np.int64],
) -> list[EquityPoint]:
    """Convert kernel equity buffers into domain facts."""
    points: list[EquityPoint] = []
    for index in range(observed_at_ns.shape[0]):
        points.append(
            EquityPoint(
                observed_at=epoch_ns_to_datetime(int(observed_at_ns[index])),
                equity=_decimal_from_float(float(result.equity[index])),
                drawdown=_decimal_from_float(float(result.drawdown[index])),
                open_position_count=int(result.open_position_count[index]),
            )
        )
    return points


def _decimal_from_float(value: float) -> Decimal:
    return Decimal(str(value))


@njit
def simulate_fixed_bars_exit_kernel(
    observed_at_ns: npt.NDArray[np.int64],
    open_prices: npt.NDArray[np.float64],
    signal_available_at_ns: npt.NDArray[np.int64],
    signal_direction: npt.NDArray[np.int8],
    signal_bar_index: npt.NDArray[np.int32],
    exit_after_bars: int,
    quantity: float,
    slippage_bps: float,
    commission_per_side: float,
    initial_capital: float,
    out_entry_signal_at_ns: npt.NDArray[np.int64],
    out_entry_fill_at_ns: npt.NDArray[np.int64],
    out_exit_signal_at_ns: npt.NDArray[np.int64],
    out_exit_fill_at_ns: npt.NDArray[np.int64],
    out_entry_fill_price: npt.NDArray[np.float64],
    out_exit_fill_price: npt.NDArray[np.float64],
    out_gross_pnl: npt.NDArray[np.float64],
    out_commission_paid: npt.NDArray[np.float64],
    out_net_pnl: npt.NDArray[np.float64],
    out_bars_held: npt.NDArray[np.int32],
    out_direction: npt.NDArray[np.int8],
    out_equity: npt.NDArray[np.float64],
    out_drawdown: npt.NDArray[np.float64],
    out_open_position_count: npt.NDArray[np.int32],
) -> int:
    bar_count = observed_at_ns.shape[0]
    signal_count = signal_available_at_ns.shape[0]
    position_open_until = -1
    trade_count = 0
    entry_fill_bar_indices = np.empty(signal_count, dtype=np.int32)
    exit_fill_bar_indices = np.empty(signal_count, dtype=np.int32)
    trade_net_pnls = np.empty(signal_count, dtype=np.float64)

    for signal_index in range(signal_count):
        signal_bar_index_value = signal_bar_index[signal_index]
        if signal_bar_index_value == UNRESOLVED_BAR_INDEX:
            continue

        entry_fill_bar_index = signal_bar_index_value + 1
        if entry_fill_bar_index >= bar_count:
            continue
        if position_open_until >= 0 and entry_fill_bar_index <= position_open_until:
            continue

        exit_signal_bar_index = entry_fill_bar_index + exit_after_bars
        exit_fill_bar_index = exit_signal_bar_index + 1
        if exit_fill_bar_index >= bar_count:
            continue

        direction = signal_direction[signal_index]
        entry_fill_price = _apply_entry_slippage(
            open_prices[entry_fill_bar_index],
            direction,
            slippage_bps,
        )
        exit_fill_price = _apply_exit_slippage(
            open_prices[exit_fill_bar_index],
            direction,
            slippage_bps,
        )
        gross_pnl = _gross_pnl(direction, quantity, entry_fill_price, exit_fill_price)
        commission_paid = commission_per_side * 2.0
        net_pnl = gross_pnl - commission_paid

        out_entry_signal_at_ns[trade_count] = signal_available_at_ns[signal_index]
        out_entry_fill_at_ns[trade_count] = observed_at_ns[entry_fill_bar_index]
        out_exit_signal_at_ns[trade_count] = observed_at_ns[exit_signal_bar_index]
        out_exit_fill_at_ns[trade_count] = observed_at_ns[exit_fill_bar_index]
        out_entry_fill_price[trade_count] = entry_fill_price
        out_exit_fill_price[trade_count] = exit_fill_price
        out_gross_pnl[trade_count] = gross_pnl
        out_commission_paid[trade_count] = commission_paid
        out_net_pnl[trade_count] = net_pnl
        out_bars_held[trade_count] = exit_fill_bar_index - entry_fill_bar_index
        out_direction[trade_count] = direction

        entry_fill_bar_indices[trade_count] = entry_fill_bar_index
        exit_fill_bar_indices[trade_count] = exit_fill_bar_index
        trade_net_pnls[trade_count] = net_pnl

        position_open_until = exit_fill_bar_index
        trade_count += 1

    closed_pnl_by_bar = np.zeros(bar_count, dtype=np.float64)
    open_delta = np.zeros(bar_count, dtype=np.int32)
    for trade_index in range(trade_count):
        exit_bar = exit_fill_bar_indices[trade_index]
        entry_bar = entry_fill_bar_indices[trade_index]
        closed_pnl_by_bar[exit_bar] += trade_net_pnls[trade_index]
        open_delta[entry_bar] += 1
        open_delta[exit_bar] -= 1

    equity = initial_capital
    peak_equity = equity
    running_open = 0
    for bar_index in range(bar_count):
        equity += closed_pnl_by_bar[bar_index]
        if equity > peak_equity:
            peak_equity = equity
        running_open += open_delta[bar_index]
        out_equity[bar_index] = equity
        out_drawdown[bar_index] = equity - peak_equity
        out_open_position_count[bar_index] = running_open

    return trade_count


@njit
def _apply_entry_slippage(price: float, direction: int, slippage_bps: float) -> float:
    adjustment = 0.0
    if slippage_bps != 0.0:
        adjustment = price * slippage_bps / _BPS_DIVISOR
    if direction == 1:
        return price + adjustment
    return price - adjustment


@njit
def _apply_exit_slippage(price: float, direction: int, slippage_bps: float) -> float:
    adjustment = 0.0
    if slippage_bps != 0.0:
        adjustment = price * slippage_bps / _BPS_DIVISOR
    if direction == 1:
        return price - adjustment
    return price + adjustment


@njit
def _gross_pnl(
    direction: int,
    quantity: float,
    entry_fill_price: float,
    exit_fill_price: float,
) -> float:
    price_delta = exit_fill_price - entry_fill_price
    if direction == 1:
        return price_delta * quantity
    return -price_delta * quantity
