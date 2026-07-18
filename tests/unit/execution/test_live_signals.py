"""Tests for live signal evaluation adapters."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.execution import (
    EmaMomentumLiveSignalEvaluator,
    StrategyModelLiveSignalEvaluator,
    required_closed_bars_for_strategy,
    resolve_live_closed_bar_window,
)
from trading_framework.market.models import MarketBar
from trading_framework.strategy import (
    BtcFuturesDemoStrategyConfig,
    build_btc_futures_demo_strategy_model,
)
from trading_framework.time.models.timeframe import Timeframe

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _bar(close: str, index: int) -> MarketBar:
    close_price = Price(Decimal(close))
    observed_at = NOW + timedelta(minutes=index)
    return MarketBar(
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Volume(1),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _evaluator(period: int = 3) -> StrategyModelLiveSignalEvaluator:
    return StrategyModelLiveSignalEvaluator(
        strategy_model=build_btc_futures_demo_strategy_model(
            BtcFuturesDemoStrategyConfig(ema_period=period)
        )
    )


def test_required_closed_bars_uses_max_component_warmup_plus_edge_lookback() -> None:
    small = build_btc_futures_demo_strategy_model(BtcFuturesDemoStrategyConfig(ema_period=3))
    large = build_btc_futures_demo_strategy_model(BtcFuturesDemoStrategyConfig(ema_period=20))
    timeframe = Timeframe("1m")

    assert required_closed_bars_for_strategy(small, timeframe=timeframe) == 4
    assert required_closed_bars_for_strategy(large, timeframe=timeframe) == 21
    assert resolve_live_closed_bar_window(required_bars=21, configured_cap=200) == 200
    assert resolve_live_closed_bar_window(required_bars=50, configured_cap=40) == 50


def test_strategy_model_live_signal_waits_for_warmup() -> None:
    evaluator = _evaluator(period=3)
    evaluation = evaluator.evaluate((_bar("100", 0), _bar("101", 1)))

    assert evaluator.required_closed_bars == 4
    assert not evaluation.condition_active
    assert not evaluation.entry_signal_active
    assert evaluation.exit_signal_active is False
    assert evaluation.ema_value is None


def test_strategy_model_live_signal_fires_on_first_true_edge() -> None:
    evaluation = _evaluator(period=3).evaluate(
        (_bar("100", 0), _bar("100", 1), _bar("100", 2), _bar("101", 3))
    )

    assert evaluation.condition_active
    assert evaluation.entry_signal_active
    assert evaluation.close == 101.0
    assert evaluation.ema_value is None


def test_strategy_model_live_signal_does_not_refire_while_condition_stays_true() -> None:
    evaluation = _evaluator(period=3).evaluate(
        (
            _bar("100", 0),
            _bar("100", 1),
            _bar("100", 2),
            _bar("101", 3),
            _bar("102", 4),
        )
    )

    assert evaluation.condition_active
    assert not evaluation.entry_signal_active


def test_strategy_model_live_signal_requires_closed_bars() -> None:
    with pytest.raises(ValidationError, match="closed_bars"):
        _evaluator().evaluate(())


def test_ema_momentum_alias_is_strategy_model_evaluator() -> None:
    assert EmaMomentumLiveSignalEvaluator is StrategyModelLiveSignalEvaluator
