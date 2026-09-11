"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.config import resolve_status_url
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.dry_run_status_card import render_dry_run_status_card
from dashboard_app.views.overview import (
    render_catalog_entry,
    render_featured_studies,
    render_future_ideas,
    render_product_thesis,
    render_recent_notes,
    render_shared_domain_map,
    render_workflow_entries,
)
from dashboard_app.views.portfolio_content import render_portfolio_evidence_entry_point

configure_page(title="Project Overview")
render_app_chrome()

st.title("Trading Research Framework")
render_product_thesis()

render_dry_run_status_card(resolve_status_url())

st.divider()
render_shared_domain_map()
st.divider()
render_workflow_entries()
st.divider()
render_featured_studies()
st.divider()
render_recent_notes()
st.divider()
render_future_ideas()
st.divider()
render_catalog_entry()
st.divider()
render_portfolio_evidence_entry_point()
