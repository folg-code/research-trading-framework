"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.overview import (
    render_product_thesis,
    render_shared_domain_map,
    render_workflow_entries,
)

configure_page(title="Project Overview")
settings = render_app_chrome()

st.title("Trading Research Framework")
render_product_thesis()

if settings is None:
    st.warning(
        "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` for deployment, "
        "or open **System diagnostics** in the sidebar for local use."
    )

st.divider()
render_shared_domain_map()
st.divider()
render_workflow_entries()
