"""Tests for the application-layer model-alias listing wrapper (T008 model picker)."""

from __future__ import annotations

from trading_framework.application.signal_research import list_known_model_aliases


def test_list_known_model_aliases_returns_both_kinds() -> None:
    aliases = list_known_model_aliases()

    assert "high_volatility" in aliases.market_model_aliases
    assert "higher_low_long" in aliases.signal_model_aliases
