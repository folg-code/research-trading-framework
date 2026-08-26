"""Tests for Predictive Research report number formatting."""

from __future__ import annotations

from trading_framework.research.reporting.predictive.formatting import (
    format_count,
    format_metric,
    format_return,
    format_share,
)


def test_format_count_uses_thousands_separator() -> None:
    assert format_count(None) == "—"
    assert format_count(0) == "0"
    assert format_count(1234) == "1,234"


def test_format_metric_and_share() -> None:
    assert format_metric(None) == "—"
    assert format_metric(0.4567) == "0.457"
    assert format_share(None) == "—"
    assert format_share(0.401) == "40.1%"


def test_format_return_shows_signed_percent() -> None:
    assert format_return(None) == "—"
    assert format_return(0.0123) == "+1.23%"
    assert format_return(-0.004) == "-0.40%"
