"""Unit tests for the non-executing alias-membership helpers (Sprint 064 T003)."""

from __future__ import annotations

from trading_framework.research.signal_research.model_registry import (
    is_known_market_model_alias,
    is_known_signal_model_alias,
)


def test_is_known_market_model_alias_true_for_built_in() -> None:
    assert is_known_market_model_alias("high_volatility") is True


def test_is_known_market_model_alias_false_for_unknown() -> None:
    assert is_known_market_model_alias("does_not_exist") is False


def test_is_known_signal_model_alias_true_for_built_in() -> None:
    assert is_known_signal_model_alias("higher_low_long") is True


def test_is_known_signal_model_alias_false_for_unknown() -> None:
    assert is_known_signal_model_alias("does_not_exist") is False
