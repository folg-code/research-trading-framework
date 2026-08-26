"""Number and label formatting for Predictive Research reports."""

from __future__ import annotations


def format_count(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}"


def format_share(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def format_metric(value: float | None, *, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def format_return(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:+.2f}%"
