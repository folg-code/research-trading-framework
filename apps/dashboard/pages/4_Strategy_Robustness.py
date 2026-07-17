"""Strategy Robustness placeholder."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Strategy Robustness")
_ = render_sidebar_storage_root()

st.title("Strategy Robustness")
st.warning("Robustness tables land in Wave C.")
