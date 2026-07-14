"""Unit tests for bar-sequential Strategy Research simulation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation import (
    BarSequentialSimulator,
    SimulationAssumptions,
)
from trading_framework.research.simulation.engine import (
    _build_bar_timestamp_index,
    _closed_pnl_by_exit_observed_at,
    _open_position_counts_by_bar_index,
    _resolve_signal_bar_index,
)
from trading_framework.research.simulation.facts import SimulatedTrade
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
    build_canonical_strategy_model,
)
from trading_framework.strategy.exit_model import ExitReason


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
    return StrategyModelDefinition(
        strategy_model_id="test_strategy",
        market_model=build_canonical_market_model_high_volatility(market_model_id="m1"),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id="s1"),
        exit_model=FixedBarsExitModel(exit_after_bars=exit_after_bars),
        risk_model=FixedQuantityRiskModel(quantity=Decimal("1")),
    )


def test_simulator_opens_and_closes_one_long_trade() -> None:
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
    assert trade["entry_fill_at"] == bars[1].observed_at
    assert trade["exit_fill_at"] == bars[4].observed_at
    assert trade["gross_pnl"] == pytest.approx(3.0)
    assert trade["net_pnl"] == pytest.approx(1.0)

    final_equity = result.equity.filter(pl.col("observed_at") == bars[4].observed_at)
    assert final_equity.row(0, named=True)["equity"] == pytest.approx(1001.0)


def test_simulator_skips_entry_when_next_bar_missing() -> None:
    bars = [_bar(0)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": ["long"],
        }
    )
    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=build_canonical_strategy_model(),
        assumptions=SimulationAssumptions(),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )
    assert len(result.trades) == 0


def test_simulator_ignores_overlapping_signals_while_position_open() -> None:
    bars = [_bar(minute) for minute in range(8)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at, bars[1].observed_at],
            "direction": ["long", "long"],
        }
    )
    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=_strategy_model(exit_after_bars=2),
        assumptions=SimulationAssumptions(),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )
    assert len(result.trades) == 1


def test_resolve_signal_bar_index_prefers_observed_at_match() -> None:
    bars = [_bar(0), _bar(1)]
    bar_index = _build_bar_timestamp_index(bars)

    assert _resolve_signal_bar_index(bar_index, available_at=bars[0].observed_at) == 0
    assert _resolve_signal_bar_index(bar_index, available_at=bars[1].available_at) == 1


def test_resolve_signal_bar_index_returns_none_for_unknown_timestamp() -> None:
    bars = [_bar(0)]
    bar_index = _build_bar_timestamp_index(bars)

    assert (
        _resolve_signal_bar_index(
            bar_index,
            available_at=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        )
        is None
    )


def test_bar_timestamp_index_keeps_first_bar_on_duplicate_observed_at() -> None:
    shared_observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    bars = [
        MarketBar(
            open=Price(Decimal("100")),
            high=Price(Decimal("101")),
            low=Price(Decimal("99")),
            close=Price(Decimal("100")),
            volume=Volume(1),
            observed_at=shared_observed_at,
            available_at=shared_observed_at + timedelta(minutes=1),
        ),
        MarketBar(
            open=Price(Decimal("101")),
            high=Price(Decimal("102")),
            low=Price(Decimal("100")),
            close=Price(Decimal("101")),
            volume=Volume(1),
            observed_at=shared_observed_at,
            available_at=shared_observed_at + timedelta(minutes=2),
        ),
    ]
    bar_index = _build_bar_timestamp_index(bars)

    assert _resolve_signal_bar_index(bar_index, available_at=shared_observed_at) == 0


def test_simulator_resolves_signal_on_available_at_when_observed_at_differs() -> None:
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
            "available_at": [bars[0].available_at],
            "direction": ["long"],
        }
    )
    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=_strategy_model(exit_after_bars=2),
        assumptions=SimulationAssumptions(),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )

    assert len(result.trades) == 1


def test_open_position_counts_track_entry_and_exit_bar_indices() -> None:
    bars = [_bar(minute) for minute in range(6)]
    bar_index = _build_bar_timestamp_index(bars)
    trades = [
        SimulatedTrade(
            trade_id="t1",
            strategy_model_id="s1",
            instrument="ES.c.0",
            direction="long",
            entry_signal_at=bars[0].observed_at,
            entry_fill_at=bars[1].observed_at,
            entry_fill_price=Decimal("100"),
            exit_signal_at=bars[3].observed_at,
            exit_fill_at=bars[4].observed_at,
            exit_fill_price=Decimal("103"),
            quantity=Decimal("1"),
            gross_pnl=Decimal("3"),
            commission_paid=Decimal("2"),
            net_pnl=Decimal("1"),
            bars_held=3,
            exit_reason=ExitReason.FIXED_BARS,
            source_dataset_ref="dataset:test:1",
        )
    ]

    open_counts = _open_position_counts_by_bar_index(
        trades,
        bar_index=bar_index,
        bar_count=len(bars),
    )

    assert open_counts == [0, 1, 1, 1, 0, 0]


def test_closed_pnl_by_exit_observed_at_aggregates_same_exit_bar() -> None:
    exit_at = datetime(2024, 1, 1, 12, 4, tzinfo=UTC)
    trades = [
        SimulatedTrade(
            trade_id="t1",
            strategy_model_id="s1",
            instrument="ES.c.0",
            direction="long",
            entry_signal_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            entry_fill_at=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            entry_fill_price=Decimal("100"),
            exit_signal_at=datetime(2024, 1, 1, 12, 3, tzinfo=UTC),
            exit_fill_at=exit_at,
            exit_fill_price=Decimal("101"),
            quantity=Decimal("1"),
            gross_pnl=Decimal("1"),
            commission_paid=Decimal("0"),
            net_pnl=Decimal("1"),
            bars_held=2,
            exit_reason=ExitReason.FIXED_BARS,
            source_dataset_ref="dataset:test:1",
        ),
        SimulatedTrade(
            trade_id="t2",
            strategy_model_id="s1",
            instrument="ES.c.0",
            direction="long",
            entry_signal_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            entry_fill_at=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
            entry_fill_price=Decimal("100"),
            exit_signal_at=datetime(2024, 1, 1, 12, 3, tzinfo=UTC),
            exit_fill_at=exit_at,
            exit_fill_price=Decimal("101"),
            quantity=Decimal("1"),
            gross_pnl=Decimal("2"),
            commission_paid=Decimal("0"),
            net_pnl=Decimal("2"),
            bars_held=2,
            exit_reason=ExitReason.FIXED_BARS,
            source_dataset_ref="dataset:test:1",
        ),
    ]

    closed_pnl = _closed_pnl_by_exit_observed_at(trades)

    assert closed_pnl[exit_at] == Decimal("3")


def test_equity_curve_applies_closed_pnl_on_exit_bar() -> None:
    bars = [_bar(minute) for minute in range(6)]
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

    open_during_trade = result.equity.filter(
        (pl.col("observed_at") >= bars[1].observed_at)
        & (pl.col("observed_at") < bars[4].observed_at)
    )
    assert open_during_trade.select(pl.col("open_position_count").max()).item() == 1
    assert (
        result.equity.filter(pl.col("observed_at") == bars[0].observed_at).row(0, named=True)[
            "open_position_count"
        ]
        == 0
    )
