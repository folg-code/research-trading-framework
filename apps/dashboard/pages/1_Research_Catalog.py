"""Research Catalog — research run catalog."""

from __future__ import annotations

import streamlit as st

from dashboard_app.caching.streamlit import cached_list_runs, storage_fingerprint
from dashboard_app.contracts import WorkflowKind
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.catalog_table import (
    build_catalog_row,
    catalog_filter_options,
    filter_catalog_runs,
)

configure_page(title="Research Catalog")
settings = render_app_chrome()

st.title("Research Catalog")
st.caption(
    "Browse persisted market, signal, strategy and robustness research runs. "
    "Live paper trading is on the **Live Paper Trading** page."
)

if settings is None:
    st.warning("Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` or use System diagnostics.")
    st.stop()

fingerprint = storage_fingerprint(settings.storage_root)
catalog = cached_list_runs(str(settings.storage_root), fingerprint.token)

counts = {kind: 0 for kind in WorkflowKind}
for item in catalog.runs:
    counts[item.workflow] = counts.get(item.workflow, 0) + 1
metric_cols = st.columns(4)
metric_cols[0].metric("Market", counts.get(WorkflowKind.MARKET, 0))
metric_cols[1].metric("Signal", counts.get(WorkflowKind.SIGNAL, 0))
metric_cols[2].metric("Strategy", counts.get(WorkflowKind.STRATEGY, 0))
metric_cols[3].metric("Robustness", counts.get(WorkflowKind.ROBUSTNESS, 0))

options = catalog_filter_options(catalog.runs)
workflow_labels = {
    "All": None,
    "Market": WorkflowKind.MARKET,
    "Signal": WorkflowKind.SIGNAL,
    "Strategy": WorkflowKind.STRATEGY,
    "Robustness": WorkflowKind.ROBUSTNESS,
}
filter_cols = st.columns(5)
with filter_cols[0]:
    workflow_label = st.selectbox("Workflow", list(workflow_labels), key="catalog_workflow")
with filter_cols[1]:
    instrument = st.selectbox(
        "Instrument",
        ["All", *options["instruments"]],
        key="catalog_instrument",
    )
with filter_cols[2]:
    timeframe = st.selectbox(
        "Timeframe",
        ["All", *options["timeframes"]],
        key="catalog_timeframe",
    )
with filter_cols[3]:
    model_query = st.text_input("Strategy / model", key="catalog_model")
with filter_cols[4]:
    date_range = st.date_input("Created (UTC)", value=(), key="catalog_dates")

date_from = date_range[0] if isinstance(date_range, tuple) and len(date_range) >= 1 else None
date_to = date_range[1] if isinstance(date_range, tuple) and len(date_range) >= 2 else date_from

filtered = filter_catalog_runs(
    catalog.runs,
    workflow=workflow_labels[workflow_label],
    instrument=None if instrument == "All" else instrument,
    timeframe=None if timeframe == "All" else timeframe,
    model_query=model_query or None,
    date_from=date_from,
    date_to=date_to,
)

st.write(f"Showing **{len(filtered)}** of **{len(catalog.runs)}** runs")
if filtered:
    rows = [build_catalog_row(item) for item in filtered]
    st.dataframe(
        [
            {
                "created": row.created,
                "workflow": row.workflow,
                "instrument": row.instrument,
                "timeframe": row.timeframe,
                "dataset": row.dataset,
                "model": row.model,
                "title": row.title,
            }
            for row in rows
        ],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Technical details", expanded=False):
        st.dataframe(
            [
                {
                    "run_id": row.run_id,
                    "title": row.title,
                    "source_dataset_ref": row.source_dataset_ref,
                    "research_scope": row.research_scope,
                    "storage_path": row.storage_path,
                }
                for row in rows
            ],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No runs match the current filters.")

if catalog.issues:
    with st.expander(f"Catalog issues ({len(catalog.issues)})"):
        for issue in catalog.issues:
            st.write(f"`{issue.path}` — {issue.reason}")
