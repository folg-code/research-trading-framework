"""Live Paper — read-only AWS dry-run status visualization."""

from __future__ import annotations

import streamlit as st

from dashboard_app.datasources import HttpAwsDryRunDataSource
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.live_paper import (
    attach_fill_markers,
    build_live_paper_candles,
    event_timeline_rows,
    live_paper_health,
)


def _fmt_num(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.4f}"
    return str(value)


def _render_snapshot(snapshot: dict[str, object]) -> None:
    health = live_paper_health(snapshot)
    if health.simulated:
        st.success("Simulated paper trading — no real orders.")
    else:
        st.warning("Status payload did not set `simulated: true`. Treat carefully.")
    if health.is_stale:
        age = (
            f"last heartbeat `{health.heartbeat_at.isoformat()}`"
            if health.heartbeat_at is not None
            else "no heartbeat"
        )
        st.warning(
            f"Status looks stale ({age}). "
            f"Worker may be stopped or unreachable (threshold {health.stale_after})."
        )

    metrics = st.columns(6)
    metrics[0].metric("Status", str(snapshot.get("status") or "—"))
    metrics[1].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[2].metric("Signal", str(snapshot.get("current_signal") or "—"))
    metrics[3].metric("Equity", _fmt_num(snapshot.get("paper_equity")))
    metrics[4].metric("Realized PnL", _fmt_num(snapshot.get("realized_pnl")))
    metrics[5].metric("Last price", _fmt_num(snapshot.get("last_price")))

    with st.expander("Runtime identity", expanded=False):
        st.write(
            {
                "runtime_id": snapshot.get("runtime_id"),
                "mode": snapshot.get("mode"),
                "provider": snapshot.get("provider"),
                "simulated": snapshot.get("simulated"),
                "last_heartbeat_at": snapshot.get("last_heartbeat_at"),
                "last_market_event_at": snapshot.get("last_market_event_at"),
                "unrealized_pnl": snapshot.get("unrealized_pnl"),
            }
        )

    chart_col, position_col = st.columns([2, 1])
    with chart_col:
        st.subheader("Recent bars")
        figure = build_live_paper_candles(snapshot.get("recent_bars"))
        figure = attach_fill_markers(figure, snapshot.get("recent_fills"))
        st.plotly_chart(figure, use_container_width=True)
    with position_col:
        st.subheader("Position")
        position = snapshot.get("current_position")
        if isinstance(position, dict):
            st.json(position)
        else:
            st.caption("Flat / no open position in this snapshot.")

    tabs = st.tabs(["Events", "Orders", "Fills", "Bars table"])
    with tabs[0]:
        events = event_timeline_rows(snapshot.get("recent_events"))
        if events:
            st.dataframe(list(events), use_container_width=True)
        else:
            st.caption("No recent events.")
    with tabs[1]:
        orders = snapshot.get("recent_orders")
        if isinstance(orders, list) and orders:
            st.dataframe(orders, use_container_width=True)
        else:
            st.caption("No recent orders.")
    with tabs[2]:
        fills = snapshot.get("recent_fills")
        if isinstance(fills, list) and fills:
            st.dataframe(fills, use_container_width=True)
        else:
            st.caption("No recent fills.")
    with tabs[3]:
        bars = snapshot.get("recent_bars")
        if isinstance(bars, list) and bars:
            st.dataframe(bars[-200:], use_container_width=True)
        else:
            st.caption("No recent bars.")


def main() -> None:
    configure_page(title="Live Paper Trading", icon="📡")
    settings = render_app_chrome()

    st.title("Live Paper Trading")
    st.caption(
        "Read-only view of the AWS paper-trading status API. "
        "The ECS worker owns execution; this page never submits orders."
    )

    if settings is None:
        st.warning(
            "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` or use System diagnostics."
        )
        return
    if not settings.status_url:
        st.info(
            "Set `DASHBOARD_STATUS_URL` (or System diagnostics when running locally) "
            "to load live paper state."
        )
        return

    col_refresh, col_auto = st.columns([1, 3])
    with col_refresh:
        refresh = st.button("Refresh", type="primary")
    with col_auto:
        st.caption("Refresh after worker heartbeats change — page stays read-only.")

    if refresh or "live_paper_snapshot" not in st.session_state:
        try:
            source = HttpAwsDryRunDataSource(status_url=settings.status_url)
            snapshot = source.fetch_session_snapshot("")
            st.session_state["live_paper_snapshot"] = snapshot
            st.session_state["live_paper_error"] = None
        except ValueError as exc:
            st.session_state["live_paper_error"] = str(exc)
            st.session_state["live_paper_snapshot"] = None

    error = st.session_state.get("live_paper_error")
    snapshot = st.session_state.get("live_paper_snapshot")
    if error:
        st.error(error)
        st.info(
            "If the worker is down, start/check ECS; the dashboard cannot recover "
            "execution state by itself."
        )
    elif isinstance(snapshot, dict):
        _render_snapshot(snapshot)
    else:
        st.info("No snapshot loaded yet — click Refresh.")


main()
