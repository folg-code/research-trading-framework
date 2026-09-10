"""Strategy Research — one representative projected simulation result."""

from __future__ import annotations

import streamlit as st

from dashboard_app.contracts import WorkflowKind
from dashboard_app.formatting import format_kpi
from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.public_catalog import build_public_catalog_row
from dashboard_app.views.workflow_evidence import (
    projected_role_fields_for_run,
    runs_for_workflow,
)

configure_page(title="Strategy Research")
render_app_chrome()

st.title("Strategy Research Evidence")
st.caption(
    "One representative persisted simulation result for a complete "
    "Market x Signal x Exit x Risk composition. These are historical simulation facts, "
    "not live performance or deployment approval."
)

bundle = load_projection_bundle_from_path(projection_bundle_path())
catalog = load_public_catalog_from_paths(projection_bundle_path(), STUDY_MANIFESTS_ROOT)
if isinstance(bundle, PublicationUnavailable) or isinstance(catalog, PublicationUnavailable):
    st.warning("Published Strategy Research evidence is unavailable for this release.")
    st.stop()

runs = runs_for_workflow(catalog.runs, WorkflowKind.STRATEGY)
if not runs:
    st.info("No safely projected Strategy Research run is included in this release.")
    st.stop()

selected = runs[0]
row = build_public_catalog_row(selected)

st.write(
    {
        "run": row.run_id,
        "model": row.model,
        "dataset": row.dataset,
        "timeframe": row.timeframe,
        "research time range": row.time_range,
        "verdict": row.verdict,
    }
)

summary = projected_role_fields_for_run(
    bundle,
    artifact_role="strategy_research_run_summary",
    run_id=selected.run_id,
)
st.subheader("Persisted simulation summary")
if summary is None:
    st.info("No allowlisted simulation summary is published for this run.")
else:
    metrics = st.columns(3)
    metrics[0].metric("Net PnL", format_kpi("net_pnl", summary.get("net_pnl")))
    metrics[1].metric("Trades", format_kpi("trade_count", summary.get("trade_count")))
    metrics[2].metric("Win rate", format_kpi("win_rate", summary.get("win_rate")))
    st.caption(
        "Values are copied from the projected summary artifact. The UI does not rerun the "
        "backtester, calculate a ranking or infer a verdict."
    )
