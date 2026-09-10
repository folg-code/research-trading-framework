"""Research Catalog — immutable public projection, grouped by study."""

from __future__ import annotations

import streamlit as st

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog_index import (
    PublicCatalogStudy,
    load_public_catalog_from_paths,
    select_public_catalog_studies,
)
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import PublicationUnavailable
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.public_catalog import (
    build_public_catalog_row,
    filter_public_catalog_runs,
    public_catalog_filter_options,
)


def _render_study(study: PublicCatalogStudy) -> None:
    label = "EDITORIAL STUDY" if study.editorial else "AUTOMATIC GROUP"
    explanation = (
        "curated by a version-controlled study manifest"
        if study.editorial
        else "no editorial study manifest; grouped deterministically by workflow and dataset"
    )
    with st.expander(f"{study.title} · {study.run_count} run(s)", expanded=study.editorial):
        st.caption(f"{label} · {explanation}")
        st.write(
            {
                "workflows": ", ".join(item.value for item in study.workflows),
                "datasets": ", ".join(study.source_dataset_refs),
                "maturity": study.maturity.value if study.maturity is not None else "UNCLASSIFIED",
            }
        )
        for experiment in study.experiments:
            st.markdown(f"#### Experiment `{experiment.experiment_id}`")
            rows = [build_public_catalog_row(run) for run in experiment.runs]
            st.dataframe(
                [
                    {
                        "created": row.created,
                        "workflow": row.workflow,
                        "instrument": row.instrument,
                        "timeframe": row.timeframe,
                        "time range": row.time_range,
                        "model": row.model,
                        "verdict": row.verdict,
                        "run_id": row.run_id,
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )


configure_page(title="Research Catalog")
render_app_chrome()

st.title("Research Catalog")
st.caption(
    "Browse immutable, sanitized research evidence grouped as study → experiment → run. "
    "The page reads the public projection only; it never scans the private workspace."
)

catalog = load_public_catalog_from_paths(projection_bundle_path(), STUDY_MANIFESTS_ROOT)
if isinstance(catalog, PublicationUnavailable):
    st.warning("The public research catalog is unavailable for this release.")
    st.caption(f"Publication status: {catalog.reason}.")
    st.stop()

counts = {kind: 0 for kind in WorkflowKind}
for run in catalog.runs:
    counts[run.workflow] = counts.get(run.workflow, 0) + 1
metric_cols = st.columns(5)
metric_cols[0].metric("Market", counts.get(WorkflowKind.MARKET, 0))
metric_cols[1].metric("Signal", counts.get(WorkflowKind.SIGNAL, 0))
metric_cols[2].metric("Strategy", counts.get(WorkflowKind.STRATEGY, 0))
metric_cols[3].metric("Robustness", counts.get(WorkflowKind.ROBUSTNESS, 0))
metric_cols[4].metric("Predictive", counts.get(WorkflowKind.PREDICTIVE, 0))

options = public_catalog_filter_options(catalog.runs)
workflow_labels = {
    "All": None,
    "Market": WorkflowKind.MARKET,
    "Signal": WorkflowKind.SIGNAL,
    "Strategy": WorkflowKind.STRATEGY,
    "Robustness": WorkflowKind.ROBUSTNESS,
    "Predictive": WorkflowKind.PREDICTIVE,
}
filter_cols = st.columns(5)
with filter_cols[0]:
    workflow_label = st.selectbox("Workflow", list(workflow_labels), key="catalog_workflow")
with filter_cols[1]:
    instrument = st.selectbox(
        "Instrument", ["All", *options["instruments"]], key="catalog_instrument"
    )
with filter_cols[2]:
    timeframe = st.selectbox("Timeframe", ["All", *options["timeframes"]], key="catalog_timeframe")
with filter_cols[3]:
    model_query = st.text_input("Strategy / model", key="catalog_model")
with filter_cols[4]:
    date_range = st.date_input("Created (UTC)", value=[], key="catalog_dates")

date_from = date_range[0] if isinstance(date_range, tuple) and len(date_range) >= 1 else None
date_to = date_range[1] if isinstance(date_range, tuple) and len(date_range) >= 2 else date_from
filtered_runs = filter_public_catalog_runs(
    catalog.runs,
    workflow=workflow_labels[workflow_label],
    instrument=None if instrument == "All" else instrument,
    timeframe=None if timeframe == "All" else timeframe,
    model_query=model_query or None,
    date_from=date_from,
    date_to=date_to,
)
filtered_studies = select_public_catalog_studies(catalog.studies, filtered_runs)

st.write(f"Showing **{len(filtered_runs)}** of **{len(catalog.runs)}** public runs")
if not filtered_runs:
    st.info("No runs match the current filters.")
else:
    for study in filtered_studies:
        _render_study(study)
