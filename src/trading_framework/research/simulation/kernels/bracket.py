"""Numba kernel for BracketExitModel (PriceBracketExit) bar-sequential simulation.

Locked semantics (D-S048-04 / ADR-0028 Section 3), implemented exactly here:

- Same-bar ambiguity: if a bar's low reaches the stop AND its high reaches
  the target in the same bar, the STOP WINS. Always. No flag, no heuristic.
- Fill price: a stop or target fills at its own trigger price, with the
  existing ``slippage_bps`` applied against the trade -- the same direction
  ``_apply_exit_slippage`` already applies for the fixed-bars kernel. The
  ``max_bars`` timeout keeps the next-bar-open convention, byte-identical to
  the fixed-bars path.
- Scan window: from the entry fill bar inclusive. A gap through the stop on
  the entry bar itself is a stop-out at the trigger price, not a skipped
  trade.
- Offsets are basis points, converted to price levels relative to the entry
  fill price (itself already adjusted for entry slippage).

Per D-S048-06 change 5 / Finding 4, this module owns its own result
dataclass and its own ``materialize_*`` functions producing a PER-TRADE
``exit_reason`` -- unlike ``kernels/fixed_bars.py``'s single scalar reason
for the whole run. ``kernels/fixed_bars.py`` is not edited by this module;
the entry/exit slippage and gross-pnl helpers are imported and reused as-is
so the fill conventions stay provably identical rather than re-derived.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import numpy.typing as npt
from numba import njit

from trading_framework.research.simulation.compile import epoch_ns_to_datetime
from trading_framework.research.simulation.facts import (
    EquityPoint,
    SimulatedTrade,
    derive_trade_id,
)
from trading_framework.research.simulation.input import (
    SIGNAL_DIRECTION_LONG,
    UNRESOLVED_BAR_INDEX,
    CompiledSimulationInput,
)
from trading_framework.research.simulation.kernels.fixed_bars import (
    _apply_entry_slippage,
    _apply_exit_slippage,
    _gross_pnl,
)
from trading_framework.signal_model.definitions import SignalDirection
from trading_framework.strategy.exit_model import ExitReason

_BPS_DIVISOR = 10_000.0

# Numba can't carry Python enums through the njit loop, so the kernel writes
# a small int code per trade and the materializer (pure Python) maps it back
# to `ExitReason`. Kept private to this module -- callers only ever see the
# materialized `ExitReason` values.
_EXIT_REASON_CODE_STOP_LOSS: int = 0
_EXIT_REASON_CODE_TAKE_PROFIT: int = 1
_EXIT_REASON_CODE_MAX_BARS: int = 2

_EXIT_REASON_BY_CODE: dict[int, ExitReason] = {
    _EXIT_REASON_CODE_STOP_LOSS: ExitReason.STOP_LOSS,
    _EXIT_REASON_CODE_TAKE_PROFIT: ExitReason.TAKE_PROFIT,
    _EXIT_REASON_CODE_MAX_BARS: ExitReason.MAX_BARS,
}


@dataclass(frozen=True, slots=True)
class BracketKernelResult:
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
    exit_reason_code: npt.NDArray[np.int8]
    equity: npt.NDArray[np.float64]
    drawdown: npt.NDArray[np.float64]
    open_position_count: npt.NDArray[np.int32]


def run_bracket_kernel(
    compiled: CompiledSimulationInput,
    *,
    stop_loss_bps: float,
    take_profit_bps: float,
    max_bars: int,
    quantity: float,
    slippage_bps: float,
    commission_per_side: float,
    initial_capital: float,
) -> BracketKernelResult:
    """Execute the bracket Numba kernel on one compiled simulation input."""
    bar_series = compiled.bars
    signal_series = compiled.entry_signals
    bar_count = bar_series.bar_count
    signal_count = int(signal_series.available_at_ns.shape[0])
    max_trades = max(signal_count, 1)

    result = BracketKernelResult(
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
        exit_reason_code=np.empty(max_trades, dtype=np.int8),
        equity=np.empty(bar_count, dtype=np.float64),
        drawdown=np.empty(bar_count, dtype=np.float64),
        open_position_count=np.empty(bar_count, dtype=np.int32),
    )
    if bar_count == 0:
        return result

    trade_count = simulate_bracket_exit_kernel(
        bar_series.observed_at_ns,
        bar_series.open_prices,
        bar_series.high_prices,
        bar_series.low_prices,
        signal_series.available_at_ns,
        signal_series.direction,
        signal_series.signal_bar_index,
        stop_loss_bps,
        take_profit_bps,
        max_bars,
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
        result.exit_reason_code,
        result.equity,
        result.drawdown,
        result.open_position_count,
    )
    return BracketKernelResult(
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
        exit_reason_code=result.exit_reason_code[:trade_count],
        equity=result.equity,
        drawdown=result.drawdown,
        open_position_count=result.open_position_count,
    )


def materialize_bracket_kernel_trades(
    result: BracketKernelResult,
    *,
    strategy_model_id: str,
    instrument: str,
    source_dataset_ref: str,
    quantity: Decimal,
) -> list[SimulatedTrade]:
    """Convert kernel trade buffers into domain facts, one exit reason per trade.

    Unlike ``fixed_bars.materialize_kernel_trades`` (one scalar reason for
    the whole run), a single bracket run can emit ``STOP_LOSS``,
    ``TAKE_PROFIT`` and ``MAX_BARS`` trades side by side, so the reason is
    read per-trade from ``result.exit_reason_code``.
    """
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
                exit_reason=_EXIT_REASON_BY_CODE[int(result.exit_reason_code[index])],
                source_dataset_ref=source_dataset_ref,
            )
        )
    return trades


def materialize_bracket_kernel_equity(
    result: BracketKernelResult,
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
def simulate_bracket_exit_kernel(
    observed_at_ns: npt.NDArray[np.int64],
    open_prices: npt.NDArray[np.float64],
    high_prices: npt.NDArray[np.float64],
    low_prices: npt.NDArray[np.float64],
    signal_available_at_ns: npt.NDArray[np.int64],
    signal_direction: npt.NDArray[np.int8],
    signal_bar_index: npt.NDArray[np.int32],
    stop_loss_bps: float,
    take_profit_bps: float,
    max_bars: int,
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
    out_exit_reason_code: npt.NDArray[np.int8],
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

        direction = signal_direction[signal_index]
        entry_fill_price = _apply_entry_slippage(
            open_prices[entry_fill_bar_index],
            direction,
            slippage_bps,
        )

        # Offsets are basis points relative to the (already slipped) entry
        # fill price. Long: stop below, target above. Short: reversed.
        if direction == 1:
            stop_price = entry_fill_price * (1.0 - stop_loss_bps / _BPS_DIVISOR)
            target_price = entry_fill_price * (1.0 + take_profit_bps / _BPS_DIVISOR)
        else:
            stop_price = entry_fill_price * (1.0 + stop_loss_bps / _BPS_DIVISOR)
            target_price = entry_fill_price * (1.0 - take_profit_bps / _BPS_DIVISOR)

        # Scan window: entry fill bar inclusive, up to (but not including)
        # the max_bars timeout signal bar, bounded by the available data.
        timeout_signal_bar_index = entry_fill_bar_index + max_bars
        scan_end = timeout_signal_bar_index - 1
        if scan_end > bar_count - 1:
            scan_end = bar_count - 1

        exit_fill_bar_index = -1
        exit_signal_bar_index = -1
        exit_fill_price = 0.0
        exit_reason_code = -1

        for bar_index in range(entry_fill_bar_index, scan_end + 1):
            if direction == 1:
                stop_hit = low_prices[bar_index] <= stop_price
                target_hit = high_prices[bar_index] >= target_price
            else:
                stop_hit = high_prices[bar_index] >= stop_price
                target_hit = low_prices[bar_index] <= target_price

            # Same-bar ambiguity: the stop always wins. Checked first, and
            # the loop breaks on either trigger -- no config flag.
            if stop_hit:
                exit_fill_bar_index = bar_index
                exit_signal_bar_index = bar_index
                exit_fill_price = _apply_exit_slippage(stop_price, direction, slippage_bps)
                exit_reason_code = _EXIT_REASON_CODE_STOP_LOSS
                break
            if target_hit:
                exit_fill_bar_index = bar_index
                exit_signal_bar_index = bar_index
                exit_fill_price = _apply_exit_slippage(target_price, direction, slippage_bps)
                exit_reason_code = _EXIT_REASON_CODE_TAKE_PROFIT
                break

        if exit_fill_bar_index == -1:
            # Neither triggered within the scan window: max_bars timeout,
            # filled at the NEXT bar's open -- identical convention to the
            # fixed-bars kernel.
            timeout_fill_bar_index = timeout_signal_bar_index + 1
            if timeout_fill_bar_index >= bar_count:
                continue
            exit_signal_bar_index = timeout_signal_bar_index
            exit_fill_bar_index = timeout_fill_bar_index
            exit_fill_price = _apply_exit_slippage(
                open_prices[exit_fill_bar_index],
                direction,
                slippage_bps,
            )
            exit_reason_code = _EXIT_REASON_CODE_MAX_BARS

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
        out_exit_reason_code[trade_count] = exit_reason_code

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
