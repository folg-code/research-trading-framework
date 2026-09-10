"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.dry_run_status_card import render_dry_run_status_card
from dashboard_app.views.overview import (
    render_product_thesis,
    render_shared_domain_map,
    render_workflow_entries,
)
from dashboard_app.views.portfolio_content import render_portfolio_evidence_entry_point

configure_page(title="Project Overview")
settings = render_app_chrome()

st.title("Trading Research Framework")
render_product_thesis()

if settings is None:
    st.warning(
        "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` for deployment, "
        "or open **System diagnostics** in the sidebar for local use."
    )

render_dry_run_status_card(settings)

st.divider()
render_shared_domain_map()
st.divider()
render_workflow_entries()
st.divider()
render_portfolio_evidence_entry_point()
