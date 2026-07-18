"""Live Paper — read-only AWS dry-run status visualization."""

from __future__ import annotations

import streamlit as st

from dashboard_app.datasources import HttpAwsDryRunDataSource
from dashboard_app.ui import configure_page, render_sidebar_storage_root


def _fmt_num(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.4f}"
    return str(value)


def _render_snapshot(snapshot: dict[str, object]) -> None:
    metrics = st.columns(5)
    metrics[0].metric("Status", str(snapshot.get("status") or "—"))
    metrics[1].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[2].metric("Signal", str(snapshot.get("current_signal") or "—"))
    metrics[3].metric("Equity", _fmt_num(snapshot.get("paper_equity")))
    metrics[4].metric("Last price", _fmt_num(snapshot.get("last_price")))

    st.write(
        {
            "runtime_id": snapshot.get("runtime_id"),
            "mode": snapshot.get("mode"),
            "provider": snapshot.get("provider"),
            "simulated": snapshot.get("simulated"),
            "last_heartbeat_at": snapshot.get("last_heartbeat_at"),
            "last_market_event_at": snapshot.get("last_market_event_at"),
            "realized_pnl": snapshot.get("realized_pnl"),
            "unrealized_pnl": snapshot.get("unrealized_pnl"),
        }
    )

    position = snapshot.get("current_position")
    st.subheader("Position")
    if isinstance(position, dict):
        st.json(position)
    else:
        st.caption("No open position in the latest snapshot.")

    for title, key in (
        ("Recent bars", "recent_bars"),
        ("Recent orders", "recent_orders"),
        ("Recent fills", "recent_fills"),
        ("Recent events", "recent_events"),
    ):
        rows = snapshot.get(key)
        st.subheader(title)
        if isinstance(rows, list) and rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.caption(f"No {key} in this snapshot.")


def main() -> None:
    configure_page(title="Live Paper", icon="📡")
    settings = render_sidebar_storage_root()

    st.title("Live Paper")
    st.caption(
        "Read-only view of the AWS paper-trading status API. "
        "The ECS worker owns execution; this page never submits orders."
    )

    if settings is None:
        st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
        return
    if not settings.status_url:
        st.info(
            "Set `DASHBOARD_STATUS_URL` or enter a status URL in the sidebar "
            "to load live paper state."
        )
        return

    st.write(f"Status URL: `{settings.status_url}`")
    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("Refresh", type="primary")
    if refresh or "live_paper_snapshot" not in st.session_state:
        try:
            source = HttpAwsDryRunDataSource(status_url=settings.status_url)
            snapshot = source.fetch_session_snapshot("")
            st.session_state["live_paper_snapshot"] = snapshot
            st.session_state["live_paper_error"] = None
        except ValueError as exc:
            st.session_state["live_paper_error"] = str(exc)
    error = st.session_state.get("live_paper_error")
    snapshot = st.session_state.get("live_paper_snapshot")
    if error:
        st.error(error)
    elif isinstance(snapshot, dict):
        _render_snapshot(snapshot)


main()
