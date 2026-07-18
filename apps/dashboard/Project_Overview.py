"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.overview import render_module_cards, render_origin_of_results

configure_page(title="Project Overview")
settings = render_app_chrome()

st.title("Trading Research Framework")
st.markdown(
    "Modular framework for market and signal research, strategy backtesting, "
    "robustness evaluation, and live paper execution."
)

if settings is None:
    st.warning(
        "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` for deployment, "
        "or open **System diagnostics** in the sidebar for local use."
    )

render_origin_of_results()
st.divider()
render_module_cards()
