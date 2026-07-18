"""Overview — research run catalog."""

from __future__ import annotations

import streamlit as st

from dashboard_app.caching.streamlit import cached_list_runs, storage_fingerprint
from dashboard_app.contracts import WorkflowKind
from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Overview")
settings = render_sidebar_storage_root()

st.title("Overview")
st.caption(
    "Read-only research catalog (MARKET / SIGNAL / STRATEGY / ROBUSTNESS). "
    "Live paper trading is on the **Live Paper** page."
)

if settings is None:
    st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
else:
    fingerprint = storage_fingerprint(settings.storage_root)
    catalog = cached_list_runs(str(settings.storage_root), fingerprint.token)
    st.write(f"Storage root: `{settings.storage_root}`")
    st.caption(f"Cache fingerprint: `{fingerprint.token}`")

    counts = {kind: 0 for kind in WorkflowKind}
    for item in catalog.runs:
        counts[item.workflow] = counts.get(item.workflow, 0) + 1
    metric_cols = st.columns(4)
    metric_cols[0].metric("Market", counts.get(WorkflowKind.MARKET, 0))
    metric_cols[1].metric("Signal", counts.get(WorkflowKind.SIGNAL, 0))
    metric_cols[2].metric("Strategy", counts.get(WorkflowKind.STRATEGY, 0))
    metric_cols[3].metric("Robustness", counts.get(WorkflowKind.ROBUSTNESS, 0))

    st.write(f"Runs: **{len(catalog.runs)}** · Catalog issues: **{len(catalog.issues)}**")
    if catalog.runs:
        st.dataframe(
            [
                {
                    "workflow": item.workflow.value,
                    "run_id": item.run_id,
                    "title": item.title,
                    "created_at_utc": (
                        item.created_at_utc.isoformat() if item.created_at_utc else None
                    ),
                    "dataset": item.source_dataset_ref,
                    "timeframe": item.evaluation_timeframe,
                    "scope": item.research_scope,
                }
                for item in catalog.runs
            ],
            use_container_width=True,
        )
    else:
        st.info(
            "No research runs found under this storage root. "
            "Mount a workspace with `research/` or produce runs locally first."
        )
    if catalog.issues:
        with st.expander(f"Catalog issues ({len(catalog.issues)})"):
            for issue in catalog.issues:
                st.write(f"`{issue.path}` — {issue.reason}")
