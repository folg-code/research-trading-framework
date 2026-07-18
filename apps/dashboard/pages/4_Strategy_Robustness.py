"""Strategy Robustness page MVP."""

from __future__ import annotations

import streamlit as st

from dashboard_app.charts import (
    build_equity_drawdown_figure,
    build_monte_carlo_percentile_figure,
    build_monte_carlo_tail_figure,
    build_parameter_sweep_surface_figure,
    build_stress_delta_figure,
    build_walk_forward_fold_figure,
)
from dashboard_app.query import DashboardQueryService
from dashboard_app.ui import configure_page, render_sidebar_storage_root
from dashboard_app.views.picker import render_run_identity, select_catalog_run
from dashboard_app.views.robustness import (
    build_verdict_checklist,
    filter_parameter_sweep_slice,
    list_parameter_sweep_slices,
    list_robustness_experiments,
    load_robustness_experiment,
)

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
    checklist = build_verdict_checklist(artifacts.verdict)
    st.subheader(f"Verdict: {checklist.verdict}")
    st.write(checklist.headline)
    if checklist.summary:
        st.caption(checklist.summary)
    if checklist.gates:
        for gate in checklist.gates:
            mark = "PASS" if gate.passed else "FAIL"
            detail = gate.message
            if gate.observed_value:
                detail = f"{detail} (observed: {gate.observed_value})"
            st.checkbox(
                f"[{mark}] {gate.label} · {gate.severity}",
                value=gate.passed,
                disabled=True,
                help=detail,
                key=f"verdict_gate_{gate.gate_id}",
            )
    if checklist.blocking_issues:
        st.error("Blocking issues")
        for item in checklist.blocking_issues:
            st.write(f"- {item}")
    if checklist.weaknesses:
        st.warning("Weaknesses")
        for item in checklist.weaknesses:
            st.write(f"- {item}")
    if checklist.strengths:
        st.success("Strengths")
        for item in checklist.strengths:
            st.write(f"- {item}")
    with st.expander("Raw verdict JSON", expanded=False):
        st.json(artifacts.verdict)
elif not artifacts.tables:
    st.warning(
        "No Parquet analytics found. Re-run robustness analysis after Sprint 028 dual-write "
        "to populate walk-forward / sweep / stress / Monte Carlo tables."
    )

if "walk_forward_folds" in artifacts.tables:
    st.subheader("Walk-forward (IS/OOS)")
    folds = artifacts.tables["walk_forward_folds"]
    if folds.num_rows:
        st.caption(
            "Training profit uses only the in-sample window that selected parameters; "
            "unseen profit is the next out-of-sample fold."
        )
        st.plotly_chart(build_walk_forward_fold_figure(folds), use_container_width=True)
    with st.expander("Fold table", expanded=False):
        st.dataframe(folds.to_pandas(), use_container_width=True)
if "walk_forward_equity" in artifacts.tables and artifacts.tables["walk_forward_equity"].num_rows:
    st.caption("Stitched equity across out-of-sample folds only.")
    st.plotly_chart(
        build_equity_drawdown_figure(artifacts.tables["walk_forward_equity"]),
        use_container_width=True,
    )

if "parameter_sweep_rankings" in artifacts.tables:
    st.subheader("Parameter sweep rankings")
    with st.expander("Rankings table", expanded=False):
        st.dataframe(
            artifacts.tables["parameter_sweep_rankings"].to_pandas(),
            use_container_width=True,
        )
if (
    "parameter_sweep_heatmap" in artifacts.tables
    and artifacts.tables["parameter_sweep_heatmap"].num_rows
):
    heat = artifacts.tables["parameter_sweep_heatmap"]
    st.subheader("Parameter sweep surface")
    slices = list_parameter_sweep_slices(heat)
    if slices:
        selected = st.selectbox(
            "Heatmap slice",
            options=list(slices),
            format_func=lambda item: item.label,
            key="robustness_sweep_slice",
        )
        slice_table = filter_parameter_sweep_slice(heat, selected)
        st.caption(
            "2D axis pairs render as a 3D surface; single-axis sweeps fall back to a line chart."
        )
        st.plotly_chart(
            build_parameter_sweep_surface_figure(
                slice_table,
                metric=selected.metric,
                x_axis=selected.x_axis,
                y_axis=selected.y_axis,
            ),
            use_container_width=True,
        )
    with st.expander("Heatmap rows", expanded=False):
        st.dataframe(heat.to_pandas(), use_container_width=True)

if "stress_comparison" in artifacts.tables:
    st.subheader("Stress tests")
    stress = artifacts.tables["stress_comparison"]
    if stress.num_rows:
        st.caption("Change in net PnL versus the unstressed baseline for each scenario.")
        st.plotly_chart(build_stress_delta_figure(stress), use_container_width=True)
    with st.expander("Stress table", expanded=False):
        st.dataframe(stress.to_pandas(), use_container_width=True)

if "monte_carlo_distributions" in artifacts.tables:
    st.subheader("Monte Carlo")
    distributions = artifacts.tables["monte_carlo_distributions"]
    if distributions.num_rows:
        st.caption("Terminal equity percentiles across reshuffled trade-order paths.")
        st.plotly_chart(
            build_monte_carlo_percentile_figure(distributions),
            use_container_width=True,
        )
    with st.expander("Distribution table", expanded=False):
        st.dataframe(distributions.to_pandas(), use_container_width=True)
if "monte_carlo_tails" in artifacts.tables:
    tails = artifacts.tables["monte_carlo_tails"]
    if tails.num_rows:
        st.caption("Tail-risk probabilities from the same Monte Carlo paths.")
        st.plotly_chart(build_monte_carlo_tail_figure(tails), use_container_width=True)
    with st.expander("Tail table", expanded=False):
        st.dataframe(tails.to_pandas(), use_container_width=True)
