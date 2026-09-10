"""Home-page BTC futures dry-run status card (Sprint 062 T005; ADR-0035).

Renders a compact, honest current/stale/offline/failed status summary and
links forward to the existing detailed Live Paper page
(``pages/5_Live_Paper_Trading.py``) -- it never duplicates that page's
content or builds a second detail/archive view.

The card is opt-in: it only renders when ``DASHBOARD_STATUS_URL`` (via
:class:`~dashboard_app.config.DashboardSettings`) is configured, mirroring
how ``pages/5_Live_Paper_Trading.py`` itself treats an unconfigured status
endpoint. When unconfigured, this module renders nothing -- no broken card,
no placeholder -- so the dashboard stays available either way.
"""

from __future__ import annotations

from typing import Protocol

import streamlit as st

from dashboard_app.config import DashboardSettings
from dashboard_app.datasources.live_paper_http import HttpLivePaperStatusDataSource
from dashboard_app.formatting import format_kpi
from dashboard_app.views.live_paper import DryRunStatusCard, build_dry_run_status_card

LIVE_PAPER_PAGE = "pages/5_Live_Paper_Trading.py"

#: The mandatory three-part simulation label (ADR-0021 / SPRINT_062.md
#: acceptance criteria). Rendered up front, before any state branching, so it
#: is visible in every state -- current, stale, offline, not-found, failed.
DRY_RUN_SIMULATION_LABELS = ("LIVE MARKET DATA", "SIMULATED EXECUTION", "NO REAL ORDERS")


class _StatusSnapshotSource(Protocol):
    """Structural contract for the status client this card consumes."""

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]: ...


def render_dry_run_status_card(
    settings: DashboardSettings | None,
    *,
    source: _StatusSnapshotSource | None = None,
) -> None:
    """Render the current dry-run status card, or nothing when unconfigured."""
    if settings is None or not settings.status_url:
        return

    st.subheader("BTC Futures Dry-Run")
    st.caption(" · ".join(DRY_RUN_SIMULATION_LABELS))

    active_source = source or HttpLivePaperStatusDataSource(status_url=settings.status_url)
    snapshot: dict[str, object] | None = None
    error: str | None = None
    try:
        snapshot = active_source.fetch_session_snapshot("")
    except ValueError as exc:
        error = str(exc)

    card = build_dry_run_status_card(status_url=settings.status_url, snapshot=snapshot, error=error)
    _render_card_body(card)
    st.page_link(LIVE_PAPER_PAGE, label="Open Live Paper Trading for full detail")


def _render_card_body(card: DryRunStatusCard) -> None:
    if card.kind == "not_configured":
        return
    if card.kind == "offline":
        st.error(
            "Dry-run status is currently unreachable. The runtime may be offline; "
            "this is not a live signal."
        )
        return
    if card.kind == "not_found":
        st.warning("No dry-run runtime state yet (not started, or a fresh deployment).")
        return
    if card.kind == "unavailable":
        st.error(f"Dry-run status is unavailable: {card.detail or 'unknown error'}")
        return

    health = card.health
    snapshot = card.snapshot
    if (
        health is None or snapshot is None
    ):  # pragma: no cover - defensive, unreachable by construction
        st.error("Dry-run status is unavailable: incomplete response.")
        return

    if card.kind == "failed":
        st.error("Worker reported FAILED. Check runtime logs / runbook.")
    elif card.kind == "stale":
        st.warning(
            f"Status is stale (heartbeat older than {health.stale_after}). Not shown as current."
        )
    else:
        st.success(f"Status: {health.badge}")

    heartbeat_text = health.heartbeat_at.isoformat() if health.heartbeat_at else "—"
    position = snapshot.get("current_position")
    quantity = position.get("quantity") if isinstance(position, dict) else None

    metrics = st.columns(4)
    metrics[0].metric("Runtime", health.badge)
    metrics[1].metric("Last heartbeat", heartbeat_text)
    metrics[2].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[3].metric("Position", str(quantity) if quantity is not None else "Flat")

    pnl_metrics = st.columns(3)
    pnl_metrics[0].metric("Equity", format_kpi("paper_equity", snapshot.get("paper_equity")))
    pnl_metrics[1].metric("Realized PnL", format_kpi("realized_pnl", snapshot.get("realized_pnl")))
    pnl_metrics[2].metric(
        "Unrealized PnL", format_kpi("unrealized_pnl", snapshot.get("unrealized_pnl"))
    )
