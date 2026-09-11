"""Strategy Execution — bounded, read-only dry-run status evidence."""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from dashboard_app.charts.lightweight import (
    candles_from_status_bars,
    markers_for_fills,
    render_lightweight_candlestick,
)
from dashboard_app.config import resolve_status_url
from dashboard_app.datasources import HttpLivePaperStatusDataSource
from dashboard_app.formatting import format_kpi
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.live_paper import (
    live_paper_health,
    sanitize_public_live_paper_snapshot,
)


def _render_snapshot(snapshot: dict[str, object]) -> None:
    health = live_paper_health(snapshot)
    st.markdown(f"### Status: **{health.badge}**")
    if not health.simulated:
        st.warning("Status payload did not confirm simulated execution. Treat it as unavailable.")
        return

    if health.heartbeat_at is None:
        st.caption("Last heartbeat: —")
    else:
        age = datetime.now(tz=UTC) - health.heartbeat_at
        st.caption(
            f"Last heartbeat: {health.heartbeat_at.isoformat()} ({int(age.total_seconds())}s ago)"
        )
    if health.is_stale:
        st.warning("The runtime snapshot is stale; it is not presented as current operation.")

    metrics = st.columns(4)
    metrics[0].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[1].metric("Signal", str(snapshot.get("current_signal") or "—"))
    metrics[2].metric("Last price", format_kpi("last_price", snapshot.get("last_price")))
    metrics[3].metric("Paper equity", format_kpi("paper_equity", snapshot.get("paper_equity")))

    st.subheader("Representative runtime evidence")
    chart_col, position_col = st.columns([2, 1])
    with chart_col:
        render_lightweight_candlestick(
            candles_from_status_bars(snapshot.get("recent_bars")),
            markers=markers_for_fills(snapshot.get("recent_fills")),
            height=420,
        )
    with position_col:
        position = snapshot.get("current_position")
        if isinstance(position, dict):
            st.write(
                {
                    "position": position.get("side") or position.get("position") or "Flat",
                    "quantity": position.get("quantity", position.get("qty", position.get("size"))),
                    "entry": position.get("entry_price") or position.get("avg_entry_price"),
                    "mark": position.get("mark_price") or snapshot.get("last_price"),
                    "unrealized PnL": format_kpi(
                        "unrealized_pnl",
                        position.get("unrealized_pnl", snapshot.get("unrealized_pnl")),
                    ),
                }
            )
        else:
            st.caption("Flat / no open position in this snapshot.")
    st.caption(
        "Only an explicit public allowlist is rendered. Raw status, orders, events, error "
        "details and unknown API fields remain private."
    )


def main() -> None:
    configure_page(title="Live Paper Trading", icon="📡")
    render_app_chrome()

    st.title("Strategy Execution Evidence")
    st.warning("LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS")
    st.caption(
        "A bounded read-only view of one dry-run runtime. The dashboard cannot submit orders, "
        "start a worker or modify execution state."
    )

    status_url = resolve_status_url()
    if status_url is None:
        st.subheader("Runtime status unavailable")
        st.write(
            {
                "runtime": "migration in progress",
                "status endpoint": "not configured",
                "execution mode": "paper / simulated only",
            }
        )
        st.caption(
            "No stale snapshot is substituted. Configure DASHBOARD_STATUS_URL when the VPS "
            "read-only endpoint is available."
        )
        return

    refresh = st.button("Refresh", type="secondary")
    if refresh or "live_paper_public_snapshot" not in st.session_state:
        try:
            source = HttpLivePaperStatusDataSource(status_url=status_url)
            raw = source.fetch_session_snapshot("")
            st.session_state["live_paper_public_snapshot"] = sanitize_public_live_paper_snapshot(
                raw
            )
            st.session_state["live_paper_public_error"] = None
        except ValueError as exc:
            st.session_state["live_paper_public_error"] = str(exc)
            st.session_state["live_paper_public_snapshot"] = None

    error = st.session_state.get("live_paper_public_error")
    snapshot = st.session_state.get("live_paper_public_snapshot")
    if error:
        st.error(error)
        st.info(
            "The dashboard leaves execution state untouched; inspect the runtime host separately."
        )
    elif isinstance(snapshot, dict):
        _render_snapshot(snapshot)
    else:
        st.info("No public runtime snapshot is available.")


main()
