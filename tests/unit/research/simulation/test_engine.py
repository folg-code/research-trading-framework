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
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.research.simulation import (
    BarSequentialSimulator,
    SimulationAssumptions,
)
from trading_framework.research.simulation.compile import compile_simulation_input
from trading_framework.research.simulation.engine import (
    SimulationEngineError,
    _build_bar_timestamp_index,
    _closed_pnl_by_exit_observed_at,
    _observed_at_index_by_ns,
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
from trading_framework.strategy.exit_model import BracketExitModel, ExitReason
from trading_framework.strategy.risk_model import EquityPercentRiskModel


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
    compiled = compile_simulation_input(
        bars=bars,
        entry_signals=pl.DataFrame(
            schema={
                "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "direction": pl.String,
            }
        ),
    )
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
        observed_at_to_index=_observed_at_index_by_ns(compiled.bars.observed_at_ns),
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


def test_simulate_rejects_unknown_exit_model_with_stable_message() -> None:
    bars = [_bar(0), _bar(1)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": ["long"],
        }
    )
    strategy_model = _strategy_model()
    object.__setattr__(strategy_model, "exit_model", object())
    with pytest.raises(SimulationEngineError) as exc_info:
        BarSequentialSimulator().simulate(
            bars=bars,
            entry_signals=entry_signals,
            strategy_model=strategy_model,
            assumptions=SimulationAssumptions(),
            instrument="ES.c.0",
            source_dataset_ref="dataset:test:1",
        )
    assert str(exc_info.value) == (
        "BarSequentialSimulator supports FixedBarsExitModel or a "
        "PriceBracketExit-conformant exit model only"
    )


def test_simulate_from_columnar_rejects_unknown_exit_model_with_stable_message() -> None:
    bars = [_bar(0), _bar(1)]
    column_batch = OhlcvColumnBatch(
        timestamps=tuple(bar.observed_at for bar in bars),
        available_at=tuple(bar.available_at for bar in bars),
        open=tuple(float(bar.open.value) for bar in bars),
        high=tuple(float(bar.high.value) for bar in bars),
        low=tuple(float(bar.low.value) for bar in bars),
        close=tuple(float(bar.close.value) for bar in bars),
        volume=tuple(float(bar.volume.value) for bar in bars),
    )
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": ["long"],
        }
    )
    strategy_model = _strategy_model()
    object.__setattr__(strategy_model, "exit_model", object())
    with pytest.raises(SimulationEngineError) as exc_info:
        BarSequentialSimulator().simulate_from_columnar(
            column_batch=column_batch,
            entry_signals=entry_signals,
            strategy_model=strategy_model,
            assumptions=SimulationAssumptions(),
            instrument="ES.c.0",
            source_dataset_ref="dataset:test:1",
        )
    assert str(exc_info.value) == (
        "BarSequentialSimulator supports FixedBarsExitModel or a "
        "PriceBracketExit-conformant exit model only"
    )


def test_simulate_accepts_structurally_conformant_risk_model() -> None:
    """A RiskModel test double, not FixedQuantityRiskModel by class, must not be rejected."""

    class _StubRiskModel:
        risk_model_id = "stub_risk"

        def position_quantity(self) -> Decimal:
            return Decimal("1")

        def allows_new_entry(self, *, open_position_count: int) -> bool:
            return open_position_count < 1

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
    strategy_model = _strategy_model(exit_after_bars=2)
    object.__setattr__(strategy_model, "risk_model", _StubRiskModel())
    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=strategy_model,
        assumptions=SimulationAssumptions(),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )
    assert len(result.trades) == 1


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


def _bracket_bar(
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


def _bracket_strategy_model(
    *, risk_model: FixedQuantityRiskModel | EquityPercentRiskModel | None = None
) -> StrategyModelDefinition:
    return StrategyModelDefinition(
        strategy_model_id="test_bracket_strategy",
        market_model=build_canonical_market_model_high_volatility(market_model_id="m1"),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id="s1"),
        exit_model=BracketExitModel(
            stop_loss_bps=100,
            take_profit_bps=200,
            max_bars=2,
        ),
        risk_model=risk_model or FixedQuantityRiskModel(quantity=Decimal("1")),
    )


def test_simulate_dispatches_bracket_exit_model_to_bracket_kernel() -> None:
    """A BracketExitModel run produces trades under more than one distinct exit_reason.

    Three sequential entries, hand-crafted so the first stops out on its own
    entry bar, the second hits its take-profit one bar later, and the third
    times out at max_bars -- proving the engine dispatches PriceBracketExit
    strategies to kernels/bracket.py rather than raising or silently falling
    back to the fixed-bars kernel (D-S048-04: stop=99, target=102 off a
    100 entry fill; max_bars=2).
    """
    bars = [
        _bracket_bar(0, open_price="100", high_price="100.2", low_price="99.8", close_price="100"),
        # entry fill for trade 1 (open=100); its own low gaps through the
        # stop (99) -> STOP_LOSS, held 0 bars. Also the signal source for
        # trade 2.
        _bracket_bar(1, open_price="100", high_price="100.5", low_price="98", close_price="99"),
        # entry fill for trade 2 (open=100); stays inside the (99, 102) band.
        _bracket_bar(2, open_price="100", high_price="101", low_price="99.5", close_price="100"),
        # target (102) breached -> TAKE_PROFIT. Also the signal source for
        # trade 3.
        _bracket_bar(3, open_price="100", high_price="102.5", low_price="99.5", close_price="102"),
        # entry fill for trade 3 (open=100); bars 4-5 stay inside the band
        # for the whole max_bars=2 scan window.
        _bracket_bar(4, open_price="100", high_price="101.5", low_price="99.5", close_price="100"),
        _bracket_bar(5, open_price="100", high_price="101.8", low_price="99.2", close_price="100"),
        # timeout signal bar (index 6); not scanned for triggers.
        _bracket_bar(6, open_price="100", high_price="100.5", low_price="99.5", close_price="100"),
        # timeout fill bar (index 7) -> MAX_BARS, filled at this bar's open.
        _bracket_bar(7, open_price="105", high_price="105.5", low_price="104.5", close_price="105"),
    ]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at, bars[1].observed_at, bars[3].observed_at],
            "direction": ["long", "long", "long"],
        }
    )

    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=_bracket_strategy_model(),
        assumptions=SimulationAssumptions(),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )

    assert len(result.trades) == 3
    exit_reasons = set(result.trades["exit_reason"].to_list())
    assert exit_reasons == {
        ExitReason.STOP_LOSS.value,
        ExitReason.TAKE_PROFIT.value,
        ExitReason.MAX_BARS.value,
    }
    assert len(exit_reasons) > 1


def test_simulate_with_equity_percent_risk_model_on_fixed_bars_kernel_runs_unchanged() -> None:
    """The isolation case (D-S048-11 E3): EquityPercentRiskModel on the UNCHANGED
    fixed-bars kernel, proving the risk-model widening (T007) is orthogonal to
    the bracket kernel dispatch (T005/T006/T008).
    """
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
    strategy_model = StrategyModelDefinition(
        strategy_model_id="test_equity_percent_strategy",
        market_model=build_canonical_market_model_high_volatility(market_model_id="m1"),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id="s1"),
        exit_model=FixedBarsExitModel(exit_after_bars=2),
        risk_model=EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("50"),
        ),
    )

    result = BarSequentialSimulator().simulate(
        bars=bars,
        entry_signals=entry_signals,
        strategy_model=strategy_model,
        assumptions=SimulationAssumptions(
            initial_capital=Decimal("1000"),
            commission_per_side=Decimal("1"),
        ),
        instrument="ES.c.0",
        source_dataset_ref="dataset:test:1",
    )

    assert len(result.trades) == 1
    trade = result.trades.row(0, named=True)
    assert trade["exit_reason"] == ExitReason.FIXED_BARS.value
    # quantity = (100000 * 0.01) / 50 = 20, derived once at construction.
    assert trade["quantity"] == pytest.approx(20.0)
    assert trade["gross_pnl"] == pytest.approx(3.0 * 20.0)
