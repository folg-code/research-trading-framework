"""Live Paper Trading — read-only AWS dry-run status visualization."""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from dashboard_app.charts.lightweight import (
    candles_from_status_bars,
    markers_for_fills,
    render_lightweight_candlestick,
)
from dashboard_app.datasources import HttpAwsDryRunDataSource
from dashboard_app.formatting import format_kpi
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.live_paper import (
    event_timeline_rows,
    live_paper_health,
)


def _render_snapshot(snapshot: dict[str, object]) -> None:
    health = live_paper_health(snapshot)
    status_raw = str(snapshot.get("status") or "unknown").lower()
    if health.is_stale:
        badge = "Stale"
    elif status_raw in {"running", "active", "ok"}:
        badge = "Running"
    elif status_raw in {"stopped", "idle"}:
        badge = "Stopped"
    elif status_raw in {"error", "failed"}:
        badge = "Error"
    else:
        badge = status_raw.title() or "Unknown"

    st.markdown(f"### Status: **{badge}**")
    if health.simulated:
        st.success("Simulated paper trading — broker abstraction only, no real orders.")
    else:
        st.warning("Status payload did not set `simulated: true`. Treat carefully.")

    now = datetime.now(tz=UTC)
    if health.heartbeat_at is not None:
        age = now - health.heartbeat_at
        age_text = f"{int(age.total_seconds())}s ago"
        st.caption(f"Last heartbeat: {health.heartbeat_at.isoformat()} ({age_text})")
    else:
        st.caption("Last heartbeat: —")
    if health.is_stale:
        st.warning(
            f"Heartbeat older than {health.stale_after}. Worker may be stopped or unreachable."
        )

    metrics = st.columns(4)
    metrics[0].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[1].metric("Signal", str(snapshot.get("current_signal") or "—"))
    metrics[2].metric("Last price", format_kpi("last_price", snapshot.get("last_price")))
    metrics[3].metric("Last update", str(snapshot.get("last_market_event_at") or "—"))

    metrics2 = st.columns(4)
    metrics2[0].metric("Equity", format_kpi("paper_equity", snapshot.get("paper_equity")))
    metrics2[1].metric("Realized PnL", format_kpi("realized_pnl", snapshot.get("realized_pnl")))
    metrics2[2].metric(
        "Unrealized PnL", format_kpi("unrealized_pnl", snapshot.get("unrealized_pnl"))
    )
    position = snapshot.get("current_position")
    if isinstance(position, dict):
        qty = position.get("quantity", position.get("qty", position.get("size")))
        metrics2[3].metric("Position", str(qty if qty is not None else "Flat"))
    else:
        metrics2[3].metric("Position", "Flat")

    chart_col, position_col = st.columns([2, 1])
    with chart_col:
        st.subheader("Recent market")
        render_lightweight_candlestick(
            candles_from_status_bars(snapshot.get("recent_bars")),
            markers=markers_for_fills(snapshot.get("recent_fills")),
            height=420,
        )
    with position_col:
        st.subheader("Position")
        if isinstance(position, dict):
            st.write(
                {
                    "Position": position.get("side") or position.get("position") or "Flat",
                    "Quantity": position.get("quantity", position.get("qty", position.get("size"))),
                    "Entry": position.get("entry_price") or position.get("avg_entry_price"),
                    "Mark": position.get("mark_price") or snapshot.get("last_price"),
                    "Unrealized PnL": format_kpi(
                        "unrealized_pnl",
                        position.get("unrealized_pnl", snapshot.get("unrealized_pnl")),
                    ),
                }
            )
        else:
            st.caption("Flat / no open position in this snapshot.")

    tabs = st.tabs(["Signals", "Orders", "Fills", "Trades", "Bars"])
    with tabs[0]:
        events = event_timeline_rows(snapshot.get("recent_events"))
        signal_events = [
            row for row in events if "signal" in str(row.get("event_type", "")).lower()
        ]
        rows = signal_events or list(events)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.caption("No recent signals.")
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
        trades = snapshot.get("recent_trades")
        if isinstance(trades, list) and trades:
            st.dataframe(trades, use_container_width=True)
        else:
            st.caption("No recent trades in this snapshot.")
    with tabs[4]:
        bars = snapshot.get("recent_bars")
        if isinstance(bars, list) and bars:
            st.dataframe(bars[-300:], use_container_width=True)
        else:
            st.caption("No recent bars.")

    with st.expander("Raw snapshot", expanded=False):
        st.json(snapshot)


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
        refresh = st.button("Refresh", type="secondary")
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
