"""Strategy Robustness page MVP."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard_app.charts import build_equity_drawdown_figure
from dashboard_app.query import DashboardQueryService
from dashboard_app.ui import configure_page, render_sidebar_storage_root
from dashboard_app.views.picker import render_run_identity, select_catalog_run
from dashboard_app.views.robustness import list_robustness_experiments, load_robustness_experiment

configure_page(title="Strategy Robustness")
settings = render_sidebar_storage_root()

st.title("Strategy Robustness")

if settings is None:
    st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
    st.stop()

service = DashboardQueryService(settings.storage_root)
experiments = list_robustness_experiments(settings.storage_root)
if not experiments:
    st.info("No robustness experiments found under this storage root.")
    st.stop()

summary = select_catalog_run(experiments, label="Experiment", key="robustness_run_picker")
artifacts = load_robustness_experiment(service, summary)

st.subheader("Experiment")
render_run_identity(summary, heading="Ids and paths")
if artifacts.verdict is not None:
    st.json(artifacts.verdict)
elif not artifacts.tables:
    st.warning(
        "No Parquet analytics found. Re-run robustness analysis after Sprint 028 dual-write "
        "to populate walk-forward / sweep / stress / Monte Carlo tables."
    )

if "walk_forward_folds" in artifacts.tables:
    st.subheader("Walk-forward (IS/OOS)")
    st.dataframe(artifacts.tables["walk_forward_folds"].to_pandas(), use_container_width=True)
if "walk_forward_equity" in artifacts.tables and artifacts.tables["walk_forward_equity"].num_rows:
    st.plotly_chart(
        build_equity_drawdown_figure(artifacts.tables["walk_forward_equity"]),
        use_container_width=True,
    )

if "parameter_sweep_rankings" in artifacts.tables:
    st.subheader("Parameter sweep rankings")
    st.dataframe(
        artifacts.tables["parameter_sweep_rankings"].to_pandas(),
        use_container_width=True,
    )
if (
    "parameter_sweep_heatmap" in artifacts.tables
    and artifacts.tables["parameter_sweep_heatmap"].num_rows
):
    heat = artifacts.tables["parameter_sweep_heatmap"].to_pandas()
    st.subheader("Parameter sweep heatmap")
    if {"x_value", "y_value", "value"}.issubset(heat.columns):
        pivot = heat.pivot_table(index="y_value", columns="x_value", values="value")
        st.plotly_chart(
            px.imshow(pivot, aspect="auto", title="Sweep heatmap"),
            use_container_width=True,
        )
    st.dataframe(heat, use_container_width=True)

if "stress_comparison" in artifacts.tables:
    st.subheader("Stress comparison")
    st.dataframe(artifacts.tables["stress_comparison"].to_pandas(), use_container_width=True)

if "monte_carlo_distributions" in artifacts.tables:
    st.subheader("Monte Carlo distributions")
    st.dataframe(
        artifacts.tables["monte_carlo_distributions"].to_pandas(),
        use_container_width=True,
    )
if "monte_carlo_tails" in artifacts.tables:
    st.subheader("Monte Carlo tails")
    st.dataframe(artifacts.tables["monte_carlo_tails"].to_pandas(), use_container_width=True)
