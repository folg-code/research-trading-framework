"""Tests for live signal evaluation adapters."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.execution import EmaMomentumLiveSignalEvaluator
from trading_framework.market.models import MarketBar
from trading_framework.strategy import (
    BtcFuturesDemoStrategyConfig,
    build_btc_futures_demo_strategy_model,
)

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


def _evaluator(period: int = 3) -> EmaMomentumLiveSignalEvaluator:
    return EmaMomentumLiveSignalEvaluator(
        build_btc_futures_demo_strategy_model(BtcFuturesDemoStrategyConfig(ema_period=period))
    )


def test_ema_momentum_live_signal_waits_for_ema_warmup() -> None:
    evaluation = _evaluator().evaluate((_bar("100", 0), _bar("101", 1)))

    assert not evaluation.condition_active
    assert not evaluation.entry_signal_active
    assert evaluation.exit_signal_active is False
    assert evaluation.ema_value is None


def test_ema_momentum_live_signal_fires_on_first_true_edge() -> None:
    evaluation = _evaluator().evaluate((_bar("100", 0), _bar("100", 1), _bar("101", 2)))

    assert evaluation.condition_active
    assert evaluation.entry_signal_active
    assert evaluation.close == 101.0
    assert evaluation.ema_value == pytest.approx(100.33333333333333)


def test_ema_momentum_live_signal_does_not_refire_while_condition_stays_true() -> None:
    evaluation = _evaluator().evaluate(
        (_bar("100", 0), _bar("100", 1), _bar("101", 2), _bar("102", 3))
    )

    assert evaluation.condition_active
    assert not evaluation.entry_signal_active


def test_ema_momentum_live_signal_requires_closed_bars() -> None:
    with pytest.raises(ValidationError, match="closed_bars"):
        _evaluator().evaluate(())
