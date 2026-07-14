"""Unit tests for Exit Model contracts."""

from __future__ import annotations

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.strategy.exit_model import ExitReason, FixedBarsExitModel


def test_fixed_bars_exit_model_computes_exit_bar_index() -> None:
    model = FixedBarsExitModel(exit_after_bars=10)
    assert model.exit_bar_index(entry_fill_bar_index=5) == 15


def test_fixed_bars_exit_model_rejects_non_positive_hold() -> None:
    with pytest.raises(ValidationError, match="exit_after_bars"):
        FixedBarsExitModel(exit_after_bars=0)


def test_fixed_bars_exit_model_default_reason() -> None:
    model = FixedBarsExitModel(exit_after_bars=3)
    assert model.default_exit_reason is ExitReason.FIXED_BARS
