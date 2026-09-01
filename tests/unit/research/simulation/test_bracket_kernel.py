"""Hand-computed fixtures for the bracket exit Numba kernel (TD-028).

There is no independent reference implementation for ``kernels/bracket.py``
(D-S048-09 / TD-028): these fixtures are the only correctness check this
kernel will ever have. Every expected trigger bar, fill price and
``exit_reason`` below is computed BY HAND from the locked semantics in
D-S048-04 -- never derived by running the kernel and asserting on its own
output.

Locked semantics under test:
    - same-bar ambiguity: stop always wins over target
    - fill price: stop/target fill at their own trigger price with adverse
      slippage; the max_bars timeout fills at the NEXT bar's open, byte
      identical to the fixed-bars convention
    - scan window: entry fill bar inclusive (a gap through the stop on the
      entry bar itself is a stop-out, not a skipped trade)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation.compile import compile_simulation_input
from trading_framework.research.simulation.input import CompiledSimulationInput
from trading_framework.research.simulation.kernels.bracket import (
    BracketKernelResult,
    materialize_bracket_kernel_trades,
    run_bracket_kernel,
)
from trading_framework.strategy.exit_model import ExitReason


def _bar(
    minute: int,
    *,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal(open_price)),
        high=Price(Decimal(high_price)),
        low=Price(Decimal(low_price)),
        close=Price(Decimal(close_price)),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(seconds=1),
    )


def _compiled(bars: list[MarketBar], *, direction: str) -> CompiledSimulationInput:
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": [direction],
        }
    )
    return compile_simulation_input(bars=bars, entry_signals=entry_signals)


def _run(
    compiled: CompiledSimulationInput,
    *,
    stop_loss_bps: float,
    take_profit_bps: float,
    max_bars: int,
    slippage_bps: float = 0.0,
) -> BracketKernelResult:
    return run_bracket_kernel(
        compiled,
        stop_loss_bps=stop_loss_bps,
        take_profit_bps=take_profit_bps,
        max_bars=max_bars,
        quantity=1.0,
        slippage_bps=slippage_bps,
        commission_per_side=0.0,
        initial_capital=1000.0,
    )


def _exit_reason(result: BracketKernelResult) -> ExitReason:
    trades = materialize_bracket_kernel_trades(
        result,
        strategy_model_id="bracket_kernel_fixture",
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
        quantity=Decimal("1"),
    )
    assert len(trades) == 1
    return trades[0].exit_reason


# ---------------------------------------------------------------------------
# stop-only: target is never reached, the stop eventually triggers
# ---------------------------------------------------------------------------


def test_long_stop_only_no_slippage() -> None:
    # entry=100, stop_bps=100 -> stop=99, tp_bps=200 -> target=102
    bars = [
        _bar(0, open_price="100", high_price="100.5", low_price="99.5", close_price="100"),
        _bar(1, open_price="100", high_price="101", low_price="99.5", close_price="100.3"),
        _bar(2, open_price="100.5", high_price="101.5", low_price="98.5", close_price="100"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.entry_fill_price[0] == pytest.approx(100.0)
    assert result.exit_fill_price[0] == pytest.approx(99.0)
    assert result.bars_held[0] == 1
    assert result.gross_pnl[0] == pytest.approx(-1.0)
    assert _exit_reason(result) == ExitReason.STOP_LOSS


def test_short_stop_only_no_slippage() -> None:
    # entry=100, stop_bps=100 -> stop=101, tp_bps=200 -> target=98
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.5", low_price="99", close_price="100"),
        _bar(2, open_price="100", high_price="101.5", low_price="98.5", close_price="100"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.entry_fill_price[0] == pytest.approx(100.0)
    assert result.exit_fill_price[0] == pytest.approx(101.0)
    assert result.bars_held[0] == 1
    assert result.gross_pnl[0] == pytest.approx(-1.0)
    assert _exit_reason(result) == ExitReason.STOP_LOSS


# ---------------------------------------------------------------------------
# target-only: stop is never reached, the target eventually triggers
# ---------------------------------------------------------------------------


def test_long_target_only_no_slippage() -> None:
    # entry=100, stop_bps=100 -> stop=99, tp_bps=200 -> target=102
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="101", low_price="99.5", close_price="100"),
        _bar(2, open_price="100", high_price="102.5", low_price="99.2", close_price="100"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(102.0)
    assert result.bars_held[0] == 1
    assert result.gross_pnl[0] == pytest.approx(2.0)
    assert _exit_reason(result) == ExitReason.TAKE_PROFIT


def test_short_target_only_no_slippage() -> None:
    # entry=100, stop_bps=100 -> stop=101, tp_bps=200 -> target=98
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.5", low_price="99", close_price="100"),
        _bar(2, open_price="100", high_price="100.8", low_price="97.5", close_price="100"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(98.0)
    assert result.bars_held[0] == 1
    assert result.gross_pnl[0] == pytest.approx(2.0)
    assert _exit_reason(result) == ExitReason.TAKE_PROFIT


# ---------------------------------------------------------------------------
# same-bar both triggerable: the stop must always win
# ---------------------------------------------------------------------------


def test_long_same_bar_both_triggerable_stop_wins() -> None:
    # entry=100, stop=99, target=102; bar2's low breaches the stop AND its
    # high breaches the target
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.5", low_price="99.5", close_price="100"),
        _bar(2, open_price="100", high_price="103", low_price="98", close_price="100"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(99.0)
    assert result.bars_held[0] == 1
    assert _exit_reason(result) == ExitReason.STOP_LOSS


def test_short_same_bar_both_triggerable_stop_wins() -> None:
    # entry=100, stop=101, target=98; bar2's high breaches the stop AND its
    # low breaches the target
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.2", low_price="99.5", close_price="100"),
        _bar(2, open_price="100", high_price="101.5", low_price="97", close_price="100"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(101.0)
    assert result.bars_held[0] == 1
    assert _exit_reason(result) == ExitReason.STOP_LOSS


# ---------------------------------------------------------------------------
# gap through the stop on the ENTRY bar itself
# ---------------------------------------------------------------------------


def test_long_gap_through_stop_on_entry_bar() -> None:
    # entry=100, stop=99; the entry fill bar's own low gaps through it
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.5", low_price="97", close_price="99"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(99.0)
    assert result.bars_held[0] == 0
    assert _exit_reason(result) == ExitReason.STOP_LOSS


def test_short_gap_through_stop_on_entry_bar() -> None:
    # entry=100, stop=101; the entry fill bar's own high gaps through it
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="102", low_price="99.5", close_price="101"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(compiled, stop_loss_bps=100, take_profit_bps=200, max_bars=5)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(101.0)
    assert result.bars_held[0] == 0
    assert _exit_reason(result) == ExitReason.STOP_LOSS


# ---------------------------------------------------------------------------
# timeout: neither stop nor target reached within max_bars
# ---------------------------------------------------------------------------


def test_long_timeout_no_slippage() -> None:
    # entry=100, stop_bps=1000 -> stop=90, tp_bps=1000 -> target=110,
    # max_bars=3: bars 1-3 stay inside (90, 110); the fill is bar5's open
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="101", low_price="99", close_price="100"),
        _bar(2, open_price="100", high_price="102", low_price="98", close_price="101"),
        _bar(3, open_price="101", high_price="103", low_price="97", close_price="102"),
        _bar(4, open_price="102", high_price="103", low_price="101", close_price="102"),
        _bar(5, open_price="104", high_price="105", low_price="103", close_price="104"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(compiled, stop_loss_bps=1000, take_profit_bps=1000, max_bars=3)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(104.0)
    assert result.bars_held[0] == 4
    assert result.gross_pnl[0] == pytest.approx(4.0)
    assert _exit_reason(result) == ExitReason.MAX_BARS


def test_short_timeout_no_slippage() -> None:
    # entry=100, stop_bps=1000 -> stop=110, tp_bps=1000 -> target=90,
    # max_bars=3: bars 1-3 stay inside (90, 110); the fill is bar5's open
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="101", low_price="99", close_price="100"),
        _bar(2, open_price="100", high_price="102", low_price="98", close_price="101"),
        _bar(3, open_price="101", high_price="103", low_price="97", close_price="102"),
        _bar(4, open_price="102", high_price="103", low_price="101", close_price="102"),
        _bar(5, open_price="96", high_price="97", low_price="95", close_price="96"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(compiled, stop_loss_bps=1000, take_profit_bps=1000, max_bars=3)

    assert result.trade_count == 1
    assert result.exit_fill_price[0] == pytest.approx(96.0)
    assert result.bars_held[0] == 4
    assert result.gross_pnl[0] == pytest.approx(4.0)
    assert _exit_reason(result) == ExitReason.MAX_BARS


# ---------------------------------------------------------------------------
# slippage applied against the trade, one fixture per exit type
# ---------------------------------------------------------------------------


def test_long_stop_with_slippage() -> None:
    # entry slippage: entry_fill = 100 * 1.01 = 101
    # stop = 101 * (1 - 0.02) = 98.98; exit slippage against a long sell:
    # 98.98 * (1 - 0.01) = 97.9902
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="101.5", low_price="99", close_price="100.5"),
        _bar(2, open_price="100", high_price="102", low_price="98", close_price="100"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(
        compiled,
        stop_loss_bps=200,
        take_profit_bps=500,
        max_bars=5,
        slippage_bps=100,
    )

    assert result.trade_count == 1
    assert result.entry_fill_price[0] == pytest.approx(101.0)
    assert result.exit_fill_price[0] == pytest.approx(97.9902)
    assert result.bars_held[0] == 1
    assert _exit_reason(result) == ExitReason.STOP_LOSS


def test_short_target_with_slippage() -> None:
    # entry slippage: entry_fill = 100 * (1 - 0.005) = 99.5
    # target = 99.5 * (1 - 0.01) = 98.505; exit slippage against a short buy:
    # 98.505 * (1 + 0.005) = 98.997525
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="100.8", low_price="99", close_price="100"),
        _bar(2, open_price="99", high_price="101", low_price="98", close_price="99.5"),
    ]
    compiled = _compiled(bars, direction="short")
    result = _run(
        compiled,
        stop_loss_bps=300,
        take_profit_bps=100,
        max_bars=5,
        slippage_bps=50,
    )

    assert result.trade_count == 1
    assert result.entry_fill_price[0] == pytest.approx(99.5)
    assert result.exit_fill_price[0] == pytest.approx(98.997525)
    assert result.bars_held[0] == 1
    assert _exit_reason(result) == ExitReason.TAKE_PROFIT


def test_long_timeout_with_slippage() -> None:
    # entry slippage: entry_fill = 100 * 1.002 = 100.2
    # stop = 100.2 * 0.9 = 90.18, target = 100.2 * 1.1 = 110.22 -- both
    # bars 1-2 stay inside that band, so the timeout fires at bar4's open
    # (103), with exit slippage against a long sell: 103 * 0.998 = 102.794
    bars = [
        _bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        _bar(1, open_price="100", high_price="101", low_price="99", close_price="100"),
        _bar(2, open_price="100", high_price="102", low_price="98", close_price="101"),
        _bar(3, open_price="102", high_price="103", low_price="101", close_price="102"),
        _bar(4, open_price="103", high_price="104", low_price="102", close_price="103"),
    ]
    compiled = _compiled(bars, direction="long")
    result = _run(
        compiled,
        stop_loss_bps=1000,
        take_profit_bps=1000,
        max_bars=2,
        slippage_bps=20,
    )

    assert result.trade_count == 1
    assert result.entry_fill_price[0] == pytest.approx(100.2)
    assert result.exit_fill_price[0] == pytest.approx(102.794)
    assert result.bars_held[0] == 3
    assert _exit_reason(result) == ExitReason.MAX_BARS
