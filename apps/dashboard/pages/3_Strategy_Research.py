"""Strategy Research placeholder."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Strategy Research")
_ = render_sidebar_storage_root()

st.title("Strategy Research")
st.warning("KPI / equity / chart / trades land in Wave B.")
