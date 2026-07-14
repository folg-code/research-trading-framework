"""Parity tests for the fixed-bars Numba simulation kernel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation import BarSequentialSimulator, SimulationAssumptions
from trading_framework.research.simulation.compile import compile_simulation_input
from trading_framework.research.simulation.facts import (
    equity_points_to_dataframe,
    simulated_trades_to_dataframe,
)
from trading_framework.research.simulation.kernels.fixed_bars import (
    materialize_kernel_equity,
    materialize_kernel_trades,
    run_fixed_bars_kernel,
)
from trading_framework.research.simulation.kernels.reference import simulate_fixed_bars_reference
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)


def _bar(minute: int, *, open_price: str = "100", close_price: str = "103") -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    open_decimal = Decimal(open_price)
    close_decimal = Decimal(close_price)
    return MarketBar(
        open=Price(open_decimal),
        high=Price(max(open_decimal, close_decimal) + Decimal("2")),
        low=Price(min(open_decimal, close_decimal) - Decimal("1")),
        close=Price(close_decimal),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _strategy_model(*, exit_after_bars: int = 2) -> StrategyModelDefinition:
    from trading_framework.application.model_evaluation.canonical_examples import (
        build_canonical_market_model_high_volatility,
        build_canonical_signal_higher_low_on_event,
    )

    return StrategyModelDefinition(
        strategy_model_id="kernel_parity_strategy",
        market_model=build_canonical_market_model_high_volatility(market_model_id="m1"),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id="s1"),
        exit_model=FixedBarsExitModel(exit_after_bars=exit_after_bars),
        risk_model=FixedQuantityRiskModel(quantity=Decimal("1")),
    )


def test_fixed_bars_kernel_matches_python_reference() -> None:
    bars = [_bar(minute) for minute in range(8)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at, bars[1].observed_at],
            "direction": ["long", "long"],
        }
    )
    strategy_model = _strategy_model(exit_after_bars=2)
    assumptions = SimulationAssumptions(
        initial_capital=Decimal("1000"),
        commission_per_side=Decimal("1"),
        slippage_bps=Decimal("0"),
    )
    compiled = compile_simulation_input(bars=bars, entry_signals=entry_signals)
    exit_model = strategy_model.exit_model
    assert isinstance(exit_model, FixedBarsExitModel)
    risk_model = strategy_model.risk_model
    assert isinstance(risk_model, FixedQuantityRiskModel)
    quantity = risk_model.position_quantity()

    reference_trades, reference_equity = simulate_fixed_bars_reference(
        compiled=compiled,
        strategy_model=strategy_model,
        assumptions=assumptions,
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
        exit_model=exit_model,
        risk_model=risk_model,
    )
    kernel_result = run_fixed_bars_kernel(
        compiled,
        exit_after_bars=exit_model.exit_after_bars,
        quantity=float(quantity),
        slippage_bps=float(assumptions.slippage_bps),
        commission_per_side=float(assumptions.commission_per_side),
        initial_capital=float(assumptions.initial_capital),
    )
    kernel_trades = materialize_kernel_trades(
        kernel_result,
        strategy_model_id=strategy_model.strategy_model_id,
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
        exit_reason=exit_model.default_exit_reason,
        quantity=quantity,
    )
    kernel_equity = materialize_kernel_equity(
        kernel_result,
        compiled.bars.observed_at_ns,
    )

    reference_trades_df = simulated_trades_to_dataframe(reference_trades)
    kernel_trades_df = simulated_trades_to_dataframe(kernel_trades)
    reference_equity_df = equity_points_to_dataframe(reference_equity)
    kernel_equity_df = equity_points_to_dataframe(kernel_equity)

    assert reference_trades_df.equals(kernel_trades_df)
    assert reference_equity_df.equals(kernel_equity_df)


def test_bar_sequential_simulator_uses_numba_kernel_path() -> None:
    bars = [
        _bar(0),
        _bar(1, open_price="100"),
        _bar(2),
        _bar(3),
        _bar(4, open_price="103"),
        _bar(5),
    ]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": ["long"],
        }
    )
    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=_strategy_model(exit_after_bars=2),
        assumptions=SimulationAssumptions(
            initial_capital=Decimal("1000"),
            commission_per_side=Decimal("1"),
        ),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )

    assert len(result.trades) == 1
    trade = result.trades.row(0, named=True)
    assert trade["gross_pnl"] == pytest.approx(3.0)
    assert trade["net_pnl"] == pytest.approx(1.0)
