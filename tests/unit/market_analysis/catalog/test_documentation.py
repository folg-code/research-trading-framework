"""Tests for registry-backed component catalog."""

from trading_framework.market_analysis.catalog import (
    format_component_entry,
    list_documented_components,
)


def test_list_documented_components_matches_registry() -> None:
    entries = list_documented_components()
    assert len(entries) == 7
    assert entries[0].component_id.value == "structure.session_range"


def test_format_component_entry_includes_schema_outputs() -> None:
    entry = next(
        item for item in list_documented_components() if item.component_id.value == "trend.ema"
    )
    rendered = format_component_entry(entry)
    assert "trend.ema" in rendered
    assert "Outputs:" in rendered
    assert "value:" in rendered
    assert "price.close > trend.ema" in rendered


def test_format_atr_and_true_range_include_dsl_examples() -> None:
    entries = {item.component_id.value: item for item in list_documented_components()}
    atr_rendered = format_component_entry(entries["volatility.atr"])
    true_range_rendered = format_component_entry(entries["volatility.true_range"])
    assert "price.close > volatility.atr(period=14)" in atr_rendered
    assert "price.close > volatility.true_range()" in true_range_rendered


def test_format_swing_includes_author_facing_dsl_examples() -> None:
    entry = next(
        item
        for item in list_documented_components()
        if item.component_id.value == "structure.swing"
    )
    rendered = format_component_entry(entry)
    assert "structure.higher_high_event" in rendered
    assert "latest_higher_low_level" in rendered
    assert "observed-index internals stay off the namespace" in rendered


def test_format_slope_includes_dsl_example() -> None:
    entry = next(
        item for item in list_documented_components() if item.component_id.value == "trend.slope"
    )
    rendered = format_component_entry(entry)
    assert "trend.slope(period=20) > 0" in rendered
    assert "period: int = 20" in rendered


def test_format_session_range_includes_dsl_examples() -> None:
    entry = next(
        item
        for item in list_documented_components()
        if item.component_id.value == "structure.session_range"
    )
    rendered = format_component_entry(entry)
    assert "structure.session_high()" in rendered
    assert "session_completed" in rendered
    assert "RTH-only" in rendered
