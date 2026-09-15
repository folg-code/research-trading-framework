"""Unit tests for the non-executing alias-membership helpers (Sprint 064 T003)."""

from __future__ import annotations

from trading_framework.research.signal_research.model_registry import (
    is_known_market_model_alias,
    is_known_signal_model_alias,
    list_known_market_model_aliases,
    list_known_signal_model_aliases,
)


def test_is_known_market_model_alias_true_for_built_in() -> None:
    assert is_known_market_model_alias("high_volatility") is True


def test_is_known_market_model_alias_false_for_unknown() -> None:
    assert is_known_market_model_alias("does_not_exist") is False


def test_is_known_signal_model_alias_true_for_built_in() -> None:
    assert is_known_signal_model_alias("higher_low_long") is True


def test_is_known_signal_model_alias_false_for_unknown() -> None:
    assert is_known_signal_model_alias("does_not_exist") is False


def test_list_known_market_model_aliases_contains_the_built_in() -> None:
    aliases = list_known_market_model_aliases()
    assert "high_volatility" in aliases
    assert aliases == tuple(sorted(aliases))


def test_list_known_signal_model_aliases_contains_the_built_ins() -> None:
    aliases = list_known_signal_model_aliases()
    assert set(aliases) == {
        "higher_low_long",
        "high_volatility_long_edge",
        "high_vol_and_higher_low",
    }
    assert aliases == tuple(sorted(aliases))
