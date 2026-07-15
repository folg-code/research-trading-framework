"""Tests for robustness report human-readable formatting."""

from __future__ import annotations

from decimal import Decimal

from trading_framework.research.robustness.report_formatting import (
    format_config_label,
    format_money,
    format_parameter_settings,
    format_probability,
    format_significant,
    format_verdict_summary,
)


def test_format_parameter_settings_uses_plain_language() -> None:
    label = format_parameter_settings({"exit_after_bars": "10"})
    assert label == "Exit after 10 bars"
    assert "cell_" not in label


def test_format_significant_limits_decimal_places() -> None:
    assert format_significant(Decimal("-590.25")) == "-590.3"
    assert format_significant(Decimal("0.123456789")) == "0.1235"
    assert format_significant(1464) == "1,464"


def test_format_money_and_probability() -> None:
    assert format_money(Decimal("99409.75")) == "99,410"
    assert format_probability(Decimal("0.1234")) == "12.3%"


def test_format_config_label_prefers_parameter_overrides() -> None:
    lookup = {"cell_0001_abc": {"exit_after_bars": "10"}}
    assert format_config_label("cell_0001_abc", lookup=lookup) == "Exit after 10 bars"
    assert format_config_label("missing", lookup=lookup) == "Strategy variant"


def test_format_verdict_summary_replaces_internal_ids() -> None:
    summary = (
        "Experiment demo passed all gates. Best grid cell: cell_0001_abc (ranking ≠ validation)."
    )
    lookup = {"cell_0001_abc": {"exit_after_bars": "10"}}
    readable = format_verdict_summary(summary, lookup=lookup)
    assert "cell_0001_abc" not in readable
    assert "Exit after 10 bars" in readable
