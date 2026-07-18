"""Plotly chart builders and overlay registry."""

from dashboard_app.charts.builders import (
    build_equity_drawdown_figure,
    build_monte_carlo_percentile_figure,
    build_monte_carlo_tail_figure,
    build_ohlcv_trade_figure,
    build_parameter_sweep_heatmap_figure,
    build_parameter_sweep_surface_figure,
    build_stress_delta_figure,
    build_walk_forward_fold_figure,
)
from dashboard_app.charts.overlays import (
    DEFAULT_OVERLAY_REGISTRY,
    OverlayKind,
    OverlayRegistration,
    OverlayRegistry,
    OverlayRenderer,
)

__all__ = [
    "DEFAULT_OVERLAY_REGISTRY",
    "OverlayKind",
    "OverlayRegistration",
    "OverlayRegistry",
    "OverlayRenderer",
    "build_equity_drawdown_figure",
    "build_monte_carlo_percentile_figure",
    "build_monte_carlo_tail_figure",
    "build_ohlcv_trade_figure",
    "build_parameter_sweep_heatmap_figure",
    "build_parameter_sweep_surface_figure",
    "build_stress_delta_figure",
    "build_walk_forward_fold_figure",
]
