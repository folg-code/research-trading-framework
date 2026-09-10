"""Market Data and Signal Research — representative public evidence."""

from __future__ import annotations

import streamlit as st

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import PublicationUnavailable
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.public_catalog import build_public_catalog_row
from dashboard_app.views.workflow_evidence import (
    format_evidence_time_range,
    representative_dataset_evidence,
    runs_for_workflow,
)

configure_page(title="Market Data and Signal Research")
render_app_chrome()

st.title("Market Data and Signal Research Evidence")
st.caption(
    "Two independent views over the immutable public projection. Market Data ends at a "
    "published DatasetRef; Signal Research consumes published data but is not its next stage."
)

catalog = load_public_catalog_from_paths(projection_bundle_path(), STUDY_MANIFESTS_ROOT)
if isinstance(catalog, PublicationUnavailable):
    st.warning("Published workflow evidence is unavailable for this release.")
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
    st.caption(
        "This is persisted dataset identity and time coverage copied through the publication "
        "allowlist. It is not a price chart and the dashboard does not open OHLCV storage."
    )

st.subheader("Signal Research · representative persisted run")
signal_runs = runs_for_workflow(catalog.runs, WorkflowKind.SIGNAL)
if not signal_runs:
    st.info(
        "No safely projected Signal Research run is included in this release. The workflow "
        "remains documented, but the dashboard does not substitute Predictive or Strategy "
        "evidence for a missing Signal Research artifact."
    )
else:
    selected = signal_runs[0]
    row = build_public_catalog_row(selected)
    st.write(
        {
            "run": row.run_id,
            "scope": row.research_scope,
            "dataset": row.dataset,
            "timeframe": row.timeframe,
            "research time range": row.time_range,
            "verdict": row.verdict,
        }
    )
    st.caption("One persisted run identity is shown; no metric or verdict is derived in the UI.")
