"""Overview — run catalog placeholder."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Overview")
settings = render_sidebar_storage_root()

st.title("Overview")
st.caption("Run catalog across MARKET / SIGNAL / STRATEGY / ROBUSTNESS workflows.")
st.warning("Catalog + `DashboardQueryService` land in the next Wave A PRs.")
if settings is None:
    st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
else:
    st.write(f"Storage root: `{settings.storage_root}`")
