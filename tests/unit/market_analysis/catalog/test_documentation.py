"""Tests for registry-backed component catalog."""

from trading_framework.market_analysis.catalog import (
    format_component_entry,
    list_documented_components,
)


def test_list_documented_components_matches_registry() -> None:
    entries = list_documented_components()
    assert len(entries) == 5
    assert entries[0].component_id.value == "structure.swing"


def test_format_component_entry_includes_schema_outputs() -> None:
    entry = next(
        item for item in list_documented_components() if item.component_id.value == "trend.ema"
    )
    rendered = format_component_entry(entry)
    assert "trend.ema" in rendered
    assert "Outputs:" in rendered
    assert "value:" in rendered
    assert "price.close > trend.ema" in rendered
