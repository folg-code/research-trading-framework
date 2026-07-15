"""Signal Research HTML report formatting helpers."""

from __future__ import annotations

from trading_framework.research.analytics.metadata import AnalyticsResultMetadata


def format_count(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}"


def format_share(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def format_hit_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def format_return(value: float | None) -> str:
    if value is None:
        return "—"
    bps = value * 10_000
    pct = value * 100
    return f"{bps:+.2f} bps ({pct:+.4f}%)"


def format_return_short(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 10_000:+.2f} bps"


def format_filter_label(metadata: AnalyticsResultMetadata) -> str:
    statuses = sorted(status.value for status in metadata.outcome_filter.aggregate_statuses)
    return ", ".join(statuses)
