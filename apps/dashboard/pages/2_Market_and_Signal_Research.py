"""Market and Signal Model Research page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard_app.query import DashboardQueryService
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.picker import render_run_identity, select_catalog_run
from dashboard_app.views.research import list_research_runs, load_research_run

configure_page(title="Market & Signal Research")
settings = render_app_chrome()

st.title("Market & Signal Research")

if settings is None:
    st.warning("Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` or use System diagnostics.")
    st.stop()

service = DashboardQueryService(settings.storage_root)
runs = list_research_runs(settings.storage_root)
if not runs:
    st.info("No Market / Signal research runs found under this storage root.")
    st.stop()

summary = select_catalog_run(runs, label="Run", key="market_signal_run_picker")
artifacts = load_research_run(service, summary)

st.subheader("Run")
render_run_identity(summary)

if "summary_metrics" not in artifacts.tables:
    st.warning(
        "Missing analytics Parquet tables — re-run / persist signal research analytics "
        "after Sprint 028 dual-write."
    )
    st.stop()

st.subheader("Summary metrics")
st.dataframe(artifacts.tables["summary_metrics"].to_pandas(), use_container_width=True)

if "grouped_summaries" in artifacts.tables and artifacts.tables["grouped_summaries"].num_rows:
    st.subheader("Grouped metrics")
    st.dataframe(artifacts.tables["grouped_summaries"].to_pandas(), use_container_width=True)

if (
    "distribution_summaries" in artifacts.tables
    and artifacts.tables["distribution_summaries"].num_rows
):
    st.subheader("Distributions")
    dist = artifacts.tables["distribution_summaries"].to_pandas()
    st.dataframe(dist, use_container_width=True)
    if {"horizon_bars", "forward_return_p10", "forward_return_p90"}.issubset(dist.columns):
        melted = dist.melt(
            id_vars=["horizon_bars"],
            value_vars=[
                col
                for col in (
                    "forward_return_p10",
                    "forward_return_p25",
                    "forward_return_p75",
                    "forward_return_p90",
                )
                if col in dist.columns
            ],
            var_name="percentile",
            value_name="forward_return",
        )
        st.plotly_chart(
            px.line(
                melted,
                x="horizon_bars",
                y="forward_return",
                color="percentile",
                markers=True,
                title="Forward-return percentiles by horizon",
            ),
            use_container_width=True,
        )

if "metric_histograms" in artifacts.tables and artifacts.tables["metric_histograms"].num_rows:
    st.subheader("Metric histograms")
    hist = artifacts.tables["metric_histograms"].to_pandas()
    st.dataframe(hist, use_container_width=True)
    if {"bin_start", "count", "metric"}.issubset(hist.columns):
        st.plotly_chart(
            px.bar(
                hist,
                x="bin_start",
                y="count",
                color="metric",
                barmode="group",
                title="Metric histogram bins",
            ),
            use_container_width=True,
        )

if "quality_warnings" in artifacts.tables and artifacts.tables["quality_warnings"].num_rows:
    st.subheader("Quality warnings")
    st.dataframe(artifacts.tables["quality_warnings"].to_pandas(), use_container_width=True)

if "join_diagnostics" in artifacts.tables and artifacts.tables["join_diagnostics"].num_rows:
    with st.expander("Join diagnostics"):
        st.dataframe(artifacts.tables["join_diagnostics"].to_pandas(), use_container_width=True)
