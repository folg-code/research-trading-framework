"""Market Data identity and rich, projection-backed Signal Research evidence."""

from __future__ import annotations

import plotly.express as px
import pyarrow as pa
import streamlit as st

from dashboard_app.formatting import humanize_dataset_ref, humanize_model_id
from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.projected_research import (
    ProjectedResearchEvidence,
    signal_research_evidence,
)
from dashboard_app.views.workflow_evidence import (
    format_evidence_time_range,
    representative_dataset_evidence,
)

configure_page(title="Market Data and Signal Research")
render_app_chrome()

st.title("Market Data and Signal Research Evidence")
st.caption(
    "Independent views over one immutable public projection. Market Data publishes reusable "
    "DatasetRefs; Signal Research evaluates market and signal hypotheses over published data."
)

projection_path = projection_bundle_path()
bundle = load_projection_bundle_from_path(projection_path)
catalog = load_public_catalog_from_paths(projection_path, STUDY_MANIFESTS_ROOT)
if isinstance(bundle, PublicationUnavailable):
    st.warning("Published workflow evidence is unavailable for this release.")
    st.caption(f"Publication status: {bundle.reason}.")
    st.stop()
if isinstance(catalog, PublicationUnavailable):
    st.warning("Published workflow catalog is unavailable for this release.")
    st.caption(f"Publication status: {catalog.reason}.")
    st.stop()

st.subheader("Market Data · representative published dataset identity")
dataset = representative_dataset_evidence(catalog.runs)
if dataset is None:
    st.info("No projected run references a published DatasetRef in this release.")
else:
    st.write(
        {
            "DatasetRef": dataset.source_dataset_ref,
            "timeframe": dataset.evaluation_timeframe or "—",
            "research time range": format_evidence_time_range(
                dataset.time_range_start_utc, dataset.time_range_end_utc
            ),
            "evidence source": f"projected run {dataset.referenced_by_run_id}",
        }
    )
    st.caption("This is persisted dataset identity and coverage, not a Market Data result.")

st.subheader("Signal Research · persisted analytical evidence")
runs = signal_research_evidence(bundle)
if not runs:
    st.info("No safely projected Signal Research analytics are included in this release.")
    st.stop()


def _overview_row(run: ProjectedResearchEvidence) -> dict[str, object]:
    fields = run.fields
    summary_table = run.table("summary_metrics")
    summary_rows = summary_table.to_pylist() if summary_table is not None else []
    warnings_table = run.table("quality_warnings")
    signal_model_ids = fields.get("signal_model_ids") or []
    return {
        "run_id": fields.get("run_id"),
        "research question": fields.get("research_question", "—"),
        "market model(s)": ", ".join(
            humanize_model_id(model_id) for model_id in fields.get("market_model_ids") or []
        )
        or "—",
        "signal model(s)": ", ".join(humanize_model_id(model_id) for model_id in signal_model_ids)
        or "—",
        "dataset": humanize_dataset_ref(fields.get("source_dataset_ref")),
        "timeframe": fields.get("evaluation_timeframe"),
        "horizons (bars)": ", ".join(str(h) for h in fields.get("horizon_bars_requested") or []),
        "sample size (total)": sum(row.get("sample_size_total") or 0 for row in summary_rows)
        or None,
        "quality warnings": warnings_table.num_rows if warnings_table is not None else 0,
    }


st.subheader("Overview — every safely projected run")
st.caption(
    "Every field below was copied from the already-projected public bundle -- no filesystem "
    "scan at request time. Click a column header to sort; a missing value sorts as "
    "unavailable, never as zero."
)
overview_table = pa.Table.from_pylist([_overview_row(run) for run in runs])
st.dataframe(overview_table.to_pandas(), use_container_width=True, hide_index=True)

st.divider()

runs_by_id = {item.artifact_id: item for item in runs}
selected_id = st.selectbox(
    "Research run",
    options=list(runs_by_id),
    format_func=lambda artifact_id: (
        f"{runs_by_id[artifact_id].fields.get('research_question', 'Signal run')} "
        f"· {runs_by_id[artifact_id].fields.get('run_id', 'unknown')}"
    ),
    key="projected_signal_research_run",
)
selected = runs_by_id[selected_id]
fields = selected.fields
st.write(
    {
        "run": fields.get("run_id", "—"),
        "experiment": fields.get("experiment_id", "—"),
        "scope": fields.get("research_scope", "—"),
        "dataset": fields.get("source_dataset_ref", "—"),
        "timeframe": fields.get("evaluation_timeframe", "—"),
        "market models": fields.get("market_model_ids", []),
        "signal models": fields.get("signal_model_ids", []),
    }
)
st.caption(
    "Every number below was copied from persisted analytics at publication time. The public "
    "application does not scan the research workspace or recompute metrics."
)

summary = selected.table("summary_metrics")
if summary is None:
    st.warning("The projected run does not contain summary metrics.")
    st.stop()
st.subheader("Summary metrics")
summary_df = summary.to_pandas()
st.dataframe(summary_df, use_container_width=True)

horizon_options = sorted(summary_df["horizon_bars"].unique().tolist())
selected_horizon = st.selectbox(
    "Horizon (bars) -- used by Adjusted forward drift and MFE/MAE relation below",
    options=horizon_options,
    key="signal_research_selected_horizon",
)

grouped = selected.table("grouped_summaries")
if grouped is not None:
    st.subheader("Grouped metrics")
    st.dataframe(grouped.to_pandas(), use_container_width=True)

distributions = selected.table("distribution_summaries")
if distributions is not None:
    st.subheader("Forward-return distributions")
    frame = distributions.to_pandas()
    st.dataframe(frame, use_container_width=True)
    percentile_columns = [
        column
        for column in (
            "forward_return_p10",
            "forward_return_p25",
            "forward_return_p75",
            "forward_return_p90",
        )
        if column in frame.columns
    ]
    if "horizon_bars" in frame.columns and percentile_columns:
        melted = frame.melt(
            id_vars=["horizon_bars"],
            value_vars=percentile_columns,
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

comparison = selected.table("conditional_comparison")
if comparison is not None:
    st.subheader("Conditional comparison")
    st.dataframe(comparison.to_pandas(), use_container_width=True)

histograms = selected.table("metric_histograms")
if histograms is not None:
    st.subheader("Metric histograms")
    histogram_frame = histograms.to_pandas()
    st.dataframe(histogram_frame, use_container_width=True)
    if {"bin_start", "count", "metric"}.issubset(histogram_frame.columns):
        st.plotly_chart(
            px.bar(
                histogram_frame,
                x="bin_start",
                y="count",
                color="metric",
                barmode="group",
                title="Metric histogram bins",
            ),
            use_container_width=True,
        )

warnings = selected.table("quality_warnings")
if warnings is not None:
    st.subheader("Quality warnings")
    st.dataframe(warnings.to_pandas(), use_container_width=True)

diagnostics = selected.table("join_diagnostics")
if diagnostics is not None:
    with st.expander("Join diagnostics"):
        st.dataframe(diagnostics.to_pandas(), use_container_width=True)

st.divider()

st.subheader("Forward-drift heatmap by context and horizon")
if grouped is None or grouped.num_rows == 0:
    st.info(
        "No grouped context/horizon summary is published for this run -- unavailable, not "
        "computed at request time."
    )
else:
    grouped_df = grouped.to_pandas()
    dimension_options = sorted(grouped_df["group_dimension"].unique().tolist())
    selected_dimension = st.selectbox(
        "Context dimension", options=dimension_options, key="signal_research_heatmap_dimension"
    )
    dimension_df = grouped_df[grouped_df["group_dimension"] == selected_dimension]
    pivot = dimension_df.pivot_table(
        index="group_value", columns="horizon_bars", values="forward_return_mean"
    )
    st.plotly_chart(
        px.imshow(
            pivot,
            aspect="auto",
            labels={"x": "horizon_bars", "y": selected_dimension, "color": "forward_return_mean"},
            title=f"Forward-return mean by {selected_dimension} and horizon",
        ),
        use_container_width=True,
    )
    st.caption(
        "Raw grouped forward-return mean, not shrinkage-adjusted -- see Adjusted forward "
        "drift below for the sample-size-weighted view."
    )

st.subheader("Adjusted forward drift")
adjusted = selected.table("adjusted_forward_drift")
if adjusted is None or adjusted.num_rows == 0:
    st.info(
        "No adjusted forward drift is published for this run -- unavailable, not computed at "
        "request time."
    )
else:
    adjusted_df = adjusted.to_pandas()
    horizon_adjusted_df = adjusted_df[adjusted_df["horizon_bars"] == selected_horizon]
    if horizon_adjusted_df.empty:
        st.info(f"No adjusted forward drift is published for horizon {selected_horizon}.")
    else:
        st.dataframe(
            horizon_adjusted_df[
                [
                    "group_dimension",
                    "group_value",
                    "sample_size_complete",
                    "forward_return_mean",
                    "global_forward_return_mean",
                    "shrinkage_weight",
                    "adjusted_forward_return_mean",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
        melted = horizon_adjusted_df.melt(
            id_vars=["group_value"],
            value_vars=["forward_return_mean", "adjusted_forward_return_mean"],
            var_name="measure",
            value_name="forward_return",
        )
        st.plotly_chart(
            px.bar(
                melted,
                x="group_value",
                y="forward_return",
                color="measure",
                barmode="group",
                title=f"Raw vs. adjusted forward-return mean (horizon {selected_horizon})",
            ),
            use_container_width=True,
        )
        st.caption(
            "`adjusted_forward_return_mean` is a sample-size-weighted shrinkage toward this "
            "run's own global mean at the same horizon -- shown beside the raw "
            "`forward_return_mean`, never replacing it. A `shrinkage_weight` near 1.0 means "
            "little adjustment (large sample); near 0.0 means the group's own mean was "
            "mostly replaced by the global mean (small sample)."
        )

st.subheader("MFE/MAE relation")
mfe_mae = selected.table("mfe_mae_pairs")
if mfe_mae is None or mfe_mae.num_rows == 0:
    st.info(
        "No MFE/MAE sample is published for this run -- unavailable, not computed at request time."
    )
else:
    mfe_mae_df = mfe_mae.to_pandas()
    horizon_mfe_mae_df = mfe_mae_df[mfe_mae_df["horizon_bars"] == selected_horizon]
    if horizon_mfe_mae_df.empty:
        st.info(f"No MFE/MAE sample is published for horizon {selected_horizon}.")
    else:
        st.plotly_chart(
            px.scatter(
                horizon_mfe_mae_df,
                x="mae",
                y="mfe",
                color="forward_return",
                title=f"Maximum favorable vs. adverse excursion (horizon {selected_horizon})",
            ),
            use_container_width=True,
        )
        st.caption(
            f"{horizon_mfe_mae_df.shape[0]:,} persisted (forward_return, mfe, mae) triples, "
            "bounded for publication -- a straight copy from the run's raw outcomes, no new "
            "computation."
        )

st.subheader("Context timeline and persistence")
timeline = selected.table("context_timeline")
persistence = selected.table("context_persistence")
timeline_empty = timeline is None or timeline.num_rows == 0
persistence_empty = persistence is None or persistence.num_rows == 0
if timeline_empty and persistence_empty:
    st.info(
        "No categorical market-context component is available for this run's Market Model -- "
        "this is not an error, just nothing to show."
    )
else:
    timeline_component_ids = (
        timeline.to_pandas()["component_id"].unique().tolist() if timeline is not None else []
    )
    persistence_component_ids = (
        persistence.to_pandas()["component_id"].unique().tolist() if persistence is not None else []
    )
    component_options = sorted({*timeline_component_ids, *persistence_component_ids})
    selected_component = st.selectbox(
        "Market context component", options=component_options, key="signal_research_component"
    )

    if timeline is not None and timeline.num_rows > 0:
        timeline_df = timeline.to_pandas()
        component_timeline_df = timeline_df[timeline_df["component_id"] == selected_component]
        st.plotly_chart(
            px.line(
                component_timeline_df,
                x="observed_at",
                y="label",
                line_shape="hv",
                title=f"Context timeline: {selected_component}",
            ),
            use_container_width=True,
        )
        st.caption(
            "Recomputed Market Analysis over this run's own published dataset, filtered to "
            "the STATE-kind component this run's Market Model actually references -- not "
            "read from any persisted Market Model result (only a single gate boolean is "
            "persisted there)."
        )
    else:
        st.info("No dated timeline is published for this component.")

    if persistence is not None and persistence.num_rows > 0:
        persistence_df = persistence.to_pandas()
        component_persistence_df = persistence_df[
            persistence_df["component_id"] == selected_component
        ]
        st.dataframe(component_persistence_df, use_container_width=True, hide_index=True)
        st.caption("A blank `end_at` means the run was still open at the series' last observation.")
    else:
        st.info("No run-length persistence is published for this component.")
