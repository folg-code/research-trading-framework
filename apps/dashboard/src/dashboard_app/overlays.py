"""Overlay renderer registry for dashboard charts (no orderflow implementation)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import plotly.graph_objects as go


class OverlayKind(StrEnum):
    """Registered overlay kinds for market/strategy charts."""

    MARKERS = "markers"
    LEVELS = "levels"
    ZONES = "zones"
    STATE_BACKGROUND = "state_background"
    TRADE_CONNECTION = "trade_connection"
    ORDERFLOW_HISTOGRAM = "orderflow_histogram"


OverlayRenderer = Callable[[go.Figure, Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class OverlayRegistration:
    """One overlay kind and its optional renderer."""

    kind: OverlayKind
    renderer: OverlayRenderer | None
    implemented: bool


def _noop_renderer(figure: go.Figure, _payload: Mapping[str, Any]) -> None:
    del figure


def _render_markers(figure: go.Figure, payload: Mapping[str, Any]) -> None:
    xs = list(payload.get("x", ()))
    ys = list(payload.get("y", ()))
    texts = list(payload.get("text", ()))
    name = str(payload.get("name", "markers"))
    marker_symbol = str(payload.get("symbol", "triangle-up"))
    marker_color = str(payload.get("color", "#2ca02c"))
    if not xs or not ys:
        return
    figure.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            name=name,
            text=texts or None,
            marker={"symbol": marker_symbol, "size": 10, "color": marker_color},
        )
    )


def _render_trade_connection(figure: go.Figure, payload: Mapping[str, Any]) -> None:
    xs = list(payload.get("x", ()))
    ys = list(payload.get("y", ()))
    name = str(payload.get("name", "trade"))
    if len(xs) < 2 or len(ys) < 2:
        return
    figure.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            name=name,
            line={"color": str(payload.get("color", "#7f7f7f")), "width": 1, "dash": "dot"},
        )
    )


_DEFAULT_REGISTRY: dict[OverlayKind, OverlayRegistration] = {
    OverlayKind.MARKERS: OverlayRegistration(
        kind=OverlayKind.MARKERS, renderer=_render_markers, implemented=True
    ),
    OverlayKind.LEVELS: OverlayRegistration(
        kind=OverlayKind.LEVELS, renderer=None, implemented=False
    ),
    OverlayKind.ZONES: OverlayRegistration(
        kind=OverlayKind.ZONES, renderer=None, implemented=False
    ),
    OverlayKind.STATE_BACKGROUND: OverlayRegistration(
        kind=OverlayKind.STATE_BACKGROUND, renderer=None, implemented=False
    ),
    OverlayKind.TRADE_CONNECTION: OverlayRegistration(
        kind=OverlayKind.TRADE_CONNECTION, renderer=_render_trade_connection, implemented=True
    ),
    OverlayKind.ORDERFLOW_HISTOGRAM: OverlayRegistration(
        kind=OverlayKind.ORDERFLOW_HISTOGRAM, renderer=None, implemented=False
    ),
}


class OverlayRegistry:
    """Lookup table for overlay renderers used by chart builders."""

    def __init__(
        self, registrations: Mapping[OverlayKind, OverlayRegistration] | None = None
    ) -> None:
        self._items = dict(registrations or _DEFAULT_REGISTRY)

    def get(self, kind: OverlayKind) -> OverlayRegistration:
        """Return registration for one overlay kind."""
        return self._items[kind]

    def apply(self, figure: go.Figure, kind: OverlayKind, payload: Mapping[str, Any]) -> bool:
        """Apply an implemented overlay; return False when kind is a placeholder."""
        registration = self.get(kind)
        if not registration.implemented or registration.renderer is None:
            return False
        registration.renderer(figure, payload)
        return True

    def implemented_kinds(self) -> tuple[OverlayKind, ...]:
        """Return overlay kinds with working renderers."""
        return tuple(kind for kind, item in self._items.items() if item.implemented)


DEFAULT_OVERLAY_REGISTRY = OverlayRegistry()
