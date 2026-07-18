"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.overview import render_module_cards, render_origin_of_results

configure_page(title="Project Overview")
settings = render_app_chrome()

st.title("Trading Research Framework")
st.markdown(
    """
Modular Python framework for market-data processing, declarative market and signal
models, strategy backtesting, robustness analysis, and live paper execution on AWS.

This public dashboard is a **read-only** view of persisted research artifacts and
live paper status. The workflow diagrams below are simplified; the full project
description, architecture, and methodology live in the
[GitHub README](https://github.com/folg-code/research-trading-framework).
"""
)

if settings is None:
    st.warning(
        "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` for deployment, "
        "or open **System diagnostics** in the sidebar for local use."
    )

render_origin_of_results()
st.divider()
render_module_cards()
