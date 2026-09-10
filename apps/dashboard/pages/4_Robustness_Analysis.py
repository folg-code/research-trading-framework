"""Robustness Research — one representative projected experiment view."""

from __future__ import annotations

import streamlit as st

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import PublicationUnavailable
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.public_catalog import build_public_catalog_row
from dashboard_app.views.workflow_evidence import runs_for_workflow

configure_page(title="Robustness Research")
render_app_chrome()

st.title("Robustness Research Evidence")
st.caption(
    "One representative persisted experiment identity. Robustness is a separate analysis "
    "over Strategy Research evidence; it is not an automatic deployment gate."
)

catalog = load_public_catalog_from_paths(projection_bundle_path(), STUDY_MANIFESTS_ROOT)
if isinstance(catalog, PublicationUnavailable):
    st.warning("Published Robustness Research evidence is unavailable for this release.")
    st.caption(f"Publication status: {catalog.reason}.")
    st.stop()

runs = runs_for_workflow(catalog.runs, WorkflowKind.ROBUSTNESS)
if not runs:
    st.info(
        "No safely projected Robustness Research experiment is included in this release. "
        "Legacy demo-robustness artifacts are intentionally not presented as portfolio "
        "research evidence."
    )
    st.stop()

row = build_public_catalog_row(runs[0])
st.write(
    {
        "experiment": row.experiment_id,
        "run": row.run_id,
        "dataset": row.dataset,
        "timeframe": row.timeframe,
        "research time range": row.time_range,
        "verdict": row.verdict,
    }
)
st.caption(
    "Only persisted, allowlisted identity and verdict fields are shown. The page does not "
    "recompute sweeps, walk-forward folds, stress tests or Monte Carlo statistics."
)
