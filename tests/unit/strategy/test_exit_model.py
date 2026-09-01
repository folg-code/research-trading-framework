"""Unit tests for Exit Model contracts."""

from __future__ import annotations

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.strategy.exit_model import (
    BracketExitModel,
    ExitModel,
    ExitReason,
    FixedBarsExitModel,
    PriceBracketExit,
)


def test_fixed_bars_exit_model_computes_exit_bar_index() -> None:
    model = FixedBarsExitModel(exit_after_bars=10)
    assert model.exit_bar_index(entry_fill_bar_index=5) == 15


def test_fixed_bars_exit_model_rejects_non_positive_hold() -> None:
    with pytest.raises(ValidationError, match="exit_after_bars"):
        FixedBarsExitModel(exit_after_bars=0)


def test_fixed_bars_exit_model_default_reason() -> None:
    model = FixedBarsExitModel(exit_after_bars=3)
    assert model.default_exit_reason is ExitReason.FIXED_BARS


def test_bracket_exit_model_exit_bar_index_is_max_bars_timeout() -> None:
    model = BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
    assert model.exit_bar_index(entry_fill_bar_index=5) == 45


def test_bracket_exit_model_satisfies_exit_model_protocol() -> None:
    model = BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
    assert isinstance(model, ExitModel)


def test_bracket_exit_model_satisfies_price_bracket_exit_protocol() -> None:
    model = BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
    assert isinstance(model, PriceBracketExit)
    assert model.stop_loss_bps == 50
    assert model.take_profit_bps == 120
    assert model.max_bars == 40


def test_bracket_exit_model_default_id() -> None:
    model = BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
    assert model.exit_model_id == "bracket"


@pytest.mark.parametrize(
    ("stop_loss_bps", "take_profit_bps", "max_bars", "match"),
    [
        (0, 120, 40, "stop_loss_bps"),
        (-1, 120, 40, "stop_loss_bps"),
        (50, 0, 40, "take_profit_bps"),
        (50, -1, 40, "take_profit_bps"),
        (50, 120, 0, "max_bars"),
        (50, 120, -1, "max_bars"),
    ],
)
def test_bracket_exit_model_rejects_invalid_fields(
    stop_loss_bps: float, take_profit_bps: float, max_bars: int, match: str
) -> None:
    with pytest.raises(ValidationError, match=match):
        BracketExitModel(
            stop_loss_bps=stop_loss_bps,
            take_profit_bps=take_profit_bps,
            max_bars=max_bars,
        )


def test_bracket_exit_model_rejects_empty_exit_model_id() -> None:
    with pytest.raises(ValidationError, match="exit_model_id"):
        BracketExitModel(
            stop_loss_bps=50,
            take_profit_bps=120,
            max_bars=40,
            exit_model_id="   ",
        )
