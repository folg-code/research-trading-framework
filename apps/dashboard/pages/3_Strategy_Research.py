"""Strategy Research — KPI, equity, windowed OHLCV, trades."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from dashboard_app.charts import build_equity_drawdown_figure, build_ohlcv_trade_figure
from dashboard_app.formatting import format_kpi, humanize_model_id
from dashboard_app.query import DashboardQueryService
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.picker import render_run_identity, select_catalog_run
from dashboard_app.views.strategy import (
    list_strategy_runs,
    load_strategy_run,
    load_trade_chart_window,
    trades_to_views,
)

configure_page(title="Strategy Research")
settings = render_app_chrome()

st.title("Strategy Research")
st.caption("PnL values are shown in points (pts) for the NQ continuous demo runs.")

if settings is None:
    st.warning("Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` or use System diagnostics.")
    st.stop()

service = DashboardQueryService(settings.storage_root)
runs = list_strategy_runs(settings.storage_root)
if not runs:
    st.info("No Strategy Research runs found under this storage root.")
    st.stop()

summary = select_catalog_run(runs, label="Run", key="strategy_run_picker")
artifacts = load_strategy_run(service, summary)

st.subheader("Run")
render_run_identity(summary)

st.subheader("KPI")
if artifacts.metrics is None:
    st.warning(
        "Missing `analytics/summary_metrics.parquet` — re-run Strategy Research after "
        "Sprint 028 dual-write to populate KPI cards."
    )
else:
    groups = [
        (
            "Performance",
            [
                ("net_pnl", "Net PnL"),
                ("total_return", "Total return"),
                ("profit_factor", "Profit factor"),
                ("sharpe_ratio", "Sharpe"),
            ],
        ),
        (
            "Risk",
            [
                ("max_drawdown", "Max drawdown"),
                ("win_rate", "Win rate"),
            ],
        ),
        (
            "Execution",
            [
                ("trade_count", "Trades"),
                ("total_costs", "Costs"),
            ],
        ),
    ]
    for group_name, keys in groups:
        st.markdown(f"**{group_name}**")
        cols = st.columns(len(keys))
        for index, (key, label) in enumerate(keys):
            cols[index].metric(label, format_kpi(key, artifacts.metrics.get(key)))

st.subheader("Equity / drawdown")
st.plotly_chart(build_equity_drawdown_figure(artifacts.equity), use_container_width=True)

trade_views = trades_to_views(artifacts.trades)
st.subheader("Trades")
if not trade_views:
    st.info("No trades in this run.")
    st.stop()

if "strategy_selected_run_id" not in st.session_state:
    st.session_state["strategy_selected_run_id"] = summary.run_id
if st.session_state["strategy_selected_run_id"] != summary.run_id:
    st.session_state["strategy_selected_run_id"] = summary.run_id
    st.session_state["strategy_trade_index"] = 0

if "strategy_trade_index" not in st.session_state:
    st.session_state["strategy_trade_index"] = 0
st.session_state["strategy_trade_index"] = min(
    st.session_state["strategy_trade_index"],
    len(trade_views) - 1,
)

nav_cols = st.columns([1, 1, 6])
if nav_cols[0].button("Prev", disabled=st.session_state["strategy_trade_index"] <= 0):
    st.session_state["strategy_trade_index"] -= 1
if nav_cols[1].button(
    "Next",
    disabled=st.session_state["strategy_trade_index"] >= len(trade_views) - 1,
):
    st.session_state["strategy_trade_index"] += 1

trade_index = st.session_state["strategy_trade_index"]
selected_trade = trade_views[trade_index]
side = humanize_model_id(selected_trade.side)
duration = "—"
if selected_trade.exit_at_utc is not None:
    held = selected_trade.exit_at_utc - selected_trade.entry_at_utc
    if isinstance(held, timedelta):
        minutes = int(held.total_seconds() // 60)
        duration = f"{minutes} min"
pnl_text = format_kpi("pnl", selected_trade.pnl)
nav_cols[2].markdown(f"**Trade {trade_index + 1} · {side} · {pnl_text} · {duration}**")

with st.expander("Trade table", expanded=False):
    st.dataframe(
        [
            {
                "trade_id": item.trade_id,
                "side": item.side,
                "entry_at_utc": item.entry_at_utc.isoformat(),
                "exit_at_utc": item.exit_at_utc.isoformat() if item.exit_at_utc else None,
                "entry_price": item.entry_price,
                "exit_price": item.exit_price,
                "pnl": format_kpi("pnl", item.pnl),
                "bars_held": item.bars_held,
            }
            for item in trade_views
        ],
        use_container_width=True,
        height=280,
    )

st.subheader("Market chart (selected trade)")
dataset_ref = summary.source_dataset_ref
timeframe = summary.evaluation_timeframe or "1m"
if not dataset_ref:
    st.warning("Run manifest has no `source_dataset_ref`; cannot load OHLCV.")
else:
    try:
        ohlcv = load_trade_chart_window(
            service,
            dataset_ref=dataset_ref,
            trade=selected_trade,
            timeframe=timeframe,
        )
    except ValueError as exc:
        st.error(f"Could not load OHLCV window: {exc}")
    else:
        if ohlcv.truncated:
            st.caption("OHLCV window truncated by max_bars.")
        if not ohlcv.bars:
            st.info(
                "No OHLCV bars in the trade window (check dataset_ref path under market_data/)."
            )
        st.plotly_chart(
            build_ohlcv_trade_figure(ohlcv.bars, selected_trade),
            use_container_width=True,
        )
