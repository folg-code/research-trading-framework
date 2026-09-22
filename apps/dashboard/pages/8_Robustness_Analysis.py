"""Rich, projection-backed legacy Robustness Research evidence."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from dashboard_app.charts import (
    build_equity_drawdown_figure,
    build_monte_carlo_percentile_figure,
    build_monte_carlo_tail_figure,
    build_parameter_sweep_heatmap_figure,
    build_parameter_sweep_surface_figure,
    build_stress_delta_figure,
    build_walk_forward_fold_figure,
)
from dashboard_app.formatting import format_kpi, format_probability
from dashboard_app.publication.paths import projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.projected_research import (
    filter_parameter_sweep,
    legacy_robustness_evidence,
    parameter_sweep_slices,
)
from dashboard_app.views.robustness import build_verdict_checklist

configure_page(title="Robustness Research")
render_app_chrome()

st.title("Robustness Research Evidence")
st.caption(
    "Walk-forward, parameter, stress and Monte Carlo evidence from one persisted historical "
    "experiment. Robustness is independent analysis, not an automatic deployment gate."
)

bundle = load_projection_bundle_from_path(projection_bundle_path())
if isinstance(bundle, PublicationUnavailable):
    st.warning("Published Robustness Research evidence is unavailable for this release.")
    st.caption(f"Publication status: {bundle.reason}.")
    st.stop()

evidence = legacy_robustness_evidence(bundle)
if evidence is None:
    st.info("No safely projected Robustness Research analytics are included in this release.")
    st.stop()

fields = evidence.fields
st.warning(
    "DEMO · LEGACY EVIDENCE — retained to demonstrate the robustness workflow. It is not "
    "presented as current Strategy Research and is excluded from Strategy catalog grouping."
)


def _format_duration_seconds(value: object) -> str:
    if not isinstance(value, int | float):
        return "—"
    return f"{value / 86_400:g}d"


st.write(
    {
        "experiment": fields.get("experiment_id", "—"),
        "dataset": fields.get("source_dataset_ref", "—"),
        "timeframe": fields.get("evaluation_timeframe", "—"),
        "research time range": (
            f"{fields.get('requested_range_start', '—')} → {fields.get('requested_range_end', '—')}"
        ),
        "strategy template": fields.get("strategy_template_id", "—"),
        "walk-forward window mode": fields.get("window_mode", "—"),
        "train / OOS / step duration": (
            f"{_format_duration_seconds(fields.get('train_duration_seconds'))} / "
            f"{_format_duration_seconds(fields.get('oos_duration_seconds'))} / "
            f"{_format_duration_seconds(fields.get('step_duration_seconds'))}"
        ),
    }
)
st.caption(
    "All values are allowlisted persisted facts copied at build time. The public application "
    "does not mount the private workspace or recompute robustness statistics."
)

verdict = fields.get("verdict")
if isinstance(verdict, Mapping):
    checklist = build_verdict_checklist(dict(verdict))
    st.subheader(f"Verdict: {checklist.verdict}")
    st.write(checklist.headline)
    if checklist.summary:
        st.caption(checklist.summary)
    for gate in checklist.gates:
        mark = "PASS" if gate.passed else "FAIL"
        observed = gate.observed_value
        observed_display: str | None
        if observed is not None and ("probability" in gate.gate_id or "ratio" in gate.gate_id):
            observed_display = format_probability(observed)
        elif observed is not None:
            observed_display = format_kpi("net_pnl", observed).replace("+", "")
        else:
            observed_display = None
        detail = gate.message
        if observed_display:
            detail = f"{detail} (observed: {observed_display})"
        if not gate.passed:
            detail = f"{detail} — failed {gate.severity} gate."
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
    with st.expander("Projected verdict", expanded=False):
        st.json(dict(verdict))

folds = evidence.table("walk_forward_folds")
if folds is not None:
    st.subheader("Walk-forward (IS/OOS)")
    st.caption("Training profit is in-sample; unseen profit is the following out-of-sample fold.")
    st.plotly_chart(build_walk_forward_fold_figure(folds), use_container_width=True)
    with st.expander("Fold table", expanded=False):
        st.dataframe(folds.to_pandas(), use_container_width=True)

fold_geometry = evidence.table("walk_forward_fold_geometry")
if fold_geometry is None or fold_geometry.num_rows == 0:
    st.info(
        "No fold geometry is published for this experiment -- unavailable, not computed at "
        "request time."
    )
else:
    st.subheader("Fold geometry and overlap")
    geometry_df = fold_geometry.to_pandas()
    train_duration_days = _format_duration_seconds(fields.get("train_duration_seconds"))
    geometry_df["train_overlap_days"] = geometry_df["train_overlap_seconds_with_previous_fold"] / (
        24 * 60 * 60
    )
    st.dataframe(
        geometry_df[
            [
                "fold_index",
                "train_range_start",
                "train_range_end",
                "oos_range_start",
                "oos_range_end",
                "train_overlap_days",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    overlapping_folds = int((geometry_df["train_overlap_seconds_with_previous_fold"] > 0).sum())
    if overlapping_folds > 0:
        max_overlap_days = float(geometry_df["train_overlap_days"].max())
        st.caption(
            f"{overlapping_folds} of {geometry_df.shape[0]} folds' training windows overlap the "
            f"previous fold's -- up to {max_overlap_days:g} of {train_duration_days} training "
            "days shared. Overlapping folds are not fully independent evidence; this is disclosed "
            "as computed, not flagged as an error."
        )
    else:
        st.caption("No fold's training window overlaps the previous fold's.")

stability = evidence.table("walk_forward_stability")
if stability is None or stability.num_rows == 0:
    st.info(
        "No rolling-window stability summary is published for this experiment -- unavailable, "
        "not computed at request time."
    )
else:
    st.subheader("Rolling-window stability")
    st.dataframe(stability.to_pandas(), use_container_width=True, hide_index=True)
    st.caption(
        "Mean/std/min/max and percent-profitable of each fold's PnL, computed once from the "
        "already-published per-fold walk-forward results above -- shown beside that raw table, "
        "never replacing it. A coefficient of variation is deliberately not shown: checked "
        "against this experiment's own numbers, it produced a meaningless ratio when the mean "
        "straddles zero."
    )

equity = evidence.table("walk_forward_equity")
if equity is not None:
    st.caption(
        "Stitched out-of-sample equity. The publication stores a deterministic, ordered "
        "presentation sample (including both endpoints) of the full persisted curve."
    )
    st.plotly_chart(build_equity_drawdown_figure(equity), use_container_width=True)

rankings = evidence.table("parameter_sweep_rankings")
if rankings is not None:
    st.subheader("Parameter sweep rankings")
    st.dataframe(rankings.to_pandas(), use_container_width=True)

heatmap = evidence.table("parameter_sweep_heatmap")
if heatmap is not None:
    st.subheader("Parameter sweep")
    slices = parameter_sweep_slices(heatmap)
    if slices:
        selected = st.selectbox(
            "Sweep slice",
            options=list(slices),
            format_func=lambda item: item.label,
            key="projected_robustness_sweep_slice",
        )
        slice_table = filter_parameter_sweep(heatmap, selected)
        if selected.y_axis:
            view_mode = st.radio(
                "View",
                options=["Heatmap 2D", "Surface 3D"],
                horizontal=True,
                key="projected_robustness_sweep_view",
            )
            if view_mode == "Heatmap 2D":
                st.plotly_chart(
                    build_parameter_sweep_heatmap_figure(
                        slice_table,
                        metric=selected.metric,
                        x_axis=selected.x_axis,
                        y_axis=selected.y_axis,
                    ),
                    use_container_width=True,
                )
            else:
                st.plotly_chart(
                    build_parameter_sweep_surface_figure(
                        slice_table,
                        metric=selected.metric,
                        x_axis=selected.x_axis,
                        y_axis=selected.y_axis,
                    ),
                    use_container_width=True,
                )
        else:
            st.plotly_chart(
                build_parameter_sweep_surface_figure(
                    slice_table,
                    metric=selected.metric,
                    x_axis=selected.x_axis,
                    y_axis=None,
                ),
                use_container_width=True,
            )
    with st.expander("Sweep rows", expanded=False):
        st.dataframe(heatmap.to_pandas(), use_container_width=True)

stress = evidence.table("stress_comparison")
if stress is not None:
    st.subheader("Stress tests")
    st.plotly_chart(build_stress_delta_figure(stress), use_container_width=True)
    st.dataframe(stress.to_pandas(), use_container_width=True)

distributions = evidence.table("monte_carlo_distributions")
tails = evidence.table("monte_carlo_tails")
if distributions is not None or tails is not None:
    st.subheader("Monte Carlo")
if distributions is not None:
    st.plotly_chart(build_monte_carlo_percentile_figure(distributions), use_container_width=True)
    st.dataframe(distributions.to_pandas(), use_container_width=True)
if tails is not None:
    st.plotly_chart(build_monte_carlo_tail_figure(tails), use_container_width=True)
    st.dataframe(tails.to_pandas(), use_container_width=True)
