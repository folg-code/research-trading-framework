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
    fills_history_rows,
    live_paper_health,
    sanitize_public_live_paper_snapshot,
)

#: How often the fragment below re-fetches and re-renders the status
#: snapshot. Kept short enough that a viewer can see the heartbeat/price
#: actually move without a manual click -- the whole point of this page is
#: to demonstrate a running workflow, not a static screenshot.
_AUTO_REFRESH_INTERVAL = "12s"


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

    feed_bits: list[str] = []
    if health.feed_connection_state:
        feed_bits.append(f"feed={health.feed_connection_state}")
    if health.feed_reconnect_count:
        feed_bits.append(f"reconnects={health.feed_reconnect_count}")
    if feed_bits:
        st.caption(" · ".join(feed_bits))

    if health.badge == "Degraded":
        st.warning("Market feed is delayed or reconnecting; process heartbeat may still be fresh.")
    elif health.is_stale:
        st.warning(
            f"The runtime snapshot is stale (heartbeat older than {health.stale_after} or "
            "worker reported stale); it is not presented as current operation."
        )
    elif health.badge == "Failed":
        st.error("Worker reported FAILED. Check runtime logs / runbook.")

    metrics = st.columns(3)
    metrics[0].metric("Symbol", str(snapshot.get("symbol") or "—"))
    metrics[1].metric("Last price", format_kpi("last_price", snapshot.get("last_price")))
    metrics[2].metric("Last update", str(snapshot.get("last_market_event_at") or "—"))

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

    st.subheader("Representative runtime evidence")
    chart_col, position_col = st.columns([2, 1])
    with chart_col:
        render_lightweight_candlestick(
            candles_from_status_bars(snapshot.get("recent_bars")),
            markers=markers_for_fills(snapshot.get("recent_fills")),
            height=420,
        )
    with position_col:
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

    st.subheader("Position history")
    history_rows = fills_history_rows(snapshot.get("recent_fills"))
    if history_rows:
        st.dataframe(history_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No simulated fills in this snapshot's recent window yet.")

    st.caption(
        "Only an explicit public allowlist is rendered. Raw status, orders, events, error "
        "details and unknown API fields remain private."
    )


@st.fragment(run_every=_AUTO_REFRESH_INTERVAL)
def _live_status_fragment(status_url: str) -> None:
    """Fetch and render the current snapshot, auto-rerunning on its own timer.

    Runs as an isolated fragment (not a full-page rerun) so the sidebar and
    rest of the app stay put while this section refreshes -- the visible
    heartbeat/price movement is the point, not a full page reload.
    """
    st.button("Refresh now", type="secondary")
    st.caption(
        f"Auto-refreshes every {_AUTO_REFRESH_INTERVAL} · "
        f"last checked {datetime.now(tz=UTC).strftime('%H:%M:%S UTC')}"
    )

    try:
        source = HttpLivePaperStatusDataSource(status_url=status_url)
        raw = source.fetch_session_snapshot("")
        snapshot: dict[str, object] | None = sanitize_public_live_paper_snapshot(raw)
        error: str | None = None
    except ValueError as exc:
        error = str(exc)
        snapshot = None

    if error:
        st.error(error)
        st.info(
            "The dashboard leaves execution state untouched; inspect the runtime host separately."
        )
    elif snapshot is not None:
        _render_snapshot(snapshot)
    else:
        st.info("No public runtime snapshot is available.")


def main() -> None:
    configure_page(title="Live Paper Trading", icon="📡")
    render_app_chrome()

    st.title("Strategy Execution Evidence")
    st.warning("LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS")
    st.caption(
        "A bounded read-only view of one dry-run runtime. The dashboard cannot submit orders, "
        "start a worker or modify execution state."
    )
    st.info(
        "This page exists to demonstrate a **working operational workflow** — a system that "
        "stays connected, reacts to live data and records its own fills — not to demonstrate a "
        "profitable strategy. The equity and PnL figures below reflect a small simulated "
        "notional and are not evidence of trading edge."
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

    _live_status_fragment(status_url)


main()
