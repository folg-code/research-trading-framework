"""Market Data identity and rich, projection-backed Signal Research evidence."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.projected_research import signal_research_evidence
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
st.dataframe(summary.to_pandas(), use_container_width=True)

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
