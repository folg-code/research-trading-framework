"""Overview — research run catalog."""

from __future__ import annotations

import streamlit as st

from dashboard_app.streamlit_cache import cached_list_runs, storage_fingerprint
from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Overview")
settings = render_sidebar_storage_root()

st.title("Overview")
st.caption("Run catalog across MARKET / SIGNAL / STRATEGY / ROBUSTNESS workflows.")

if settings is None:
    st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
else:
    fingerprint = storage_fingerprint(settings.storage_root)
    catalog = cached_list_runs(str(settings.storage_root), fingerprint.token)
    st.write(f"Storage root: `{settings.storage_root}`")
    st.caption(f"Cache fingerprint: `{fingerprint.token}`")
    st.write(f"Runs: **{len(catalog.runs)}** · Issues: **{len(catalog.issues)}**")
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
        st.info("No research runs found under this storage root.")
    if catalog.issues:
        with st.expander(f"Catalog issues ({len(catalog.issues)})"):
            for issue in catalog.issues:
                st.write(f"`{issue.path}` — {issue.reason}")
