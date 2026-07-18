"""Shared Plotly visual style for public dashboard charts."""

from __future__ import annotations

from typing import Any

COLOR_LONG = "#2ca02c"
COLOR_SHORT = "#d62728"
COLOR_OOS = "#1f4e79"
COLOR_IS = "#9e9e9e"
COLOR_POSITIVE = "#2ca02c"
COLOR_NEGATIVE = "#d62728"
COLOR_NEUTRAL = "#4C78A8"

DEFAULT_LAYOUT: dict[str, Any] = {
    "font": {"family": "Inter, Segoe UI, sans-serif", "size": 13},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    "margin": {"l": 48, "r": 24, "t": 48, "b": 40},
    "template": "plotly_white",
}


def apply_public_layout(figure: Any, *, title: str | None = None, height: int = 420) -> Any:
    """Apply consistent public-demo layout to a Plotly figure."""
    updates: dict[str, Any] = {**DEFAULT_LAYOUT, "height": height}
    if title:
        updates["title"] = title
    figure.update_layout(**updates)
    figure.update_xaxes(showgrid=True, gridcolor="#eceff1")
    figure.update_yaxes(showgrid=True, gridcolor="#eceff1")
    return figure
