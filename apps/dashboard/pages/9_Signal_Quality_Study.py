"""Signal Quality study page: study view plus Explore Evidence."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import METHODOLOGY_PAGE
from dashboard_app.views.study import render_btc_signal_quality_study

configure_page(title="Signal Quality Study")
render_app_chrome()

render_btc_signal_quality_study()

st.divider()
st.subheader("Explore Evidence")
st.caption(
    "The persisted predictive run and Strategy Research runs behind this study, "
    "with full folds, verdict facts, and provenance."
)
evidence_columns = st.columns(2)
evidence_columns[0].page_link(
    "pages/6_Predictive_Research.py", label="Explore Predictive Research evidence"
)
evidence_columns[1].page_link(
    "pages/3_Strategy_Research.py", label="Explore Strategy Research evidence"
)

st.page_link(METHODOLOGY_PAGE, label="Back to Signal Quality Methodology")
