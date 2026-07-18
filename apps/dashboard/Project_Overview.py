"""Trading research dashboard — Project Overview."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_app_chrome

configure_page(title="Project Overview")
settings = render_app_chrome()

st.title("Trading Research Framework")
st.markdown(
    "Modular framework for market and signal research, strategy backtesting, "
    "robustness evaluation and live paper execution."
)

if settings is None:
    st.warning(
        "Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` for deployment, "
        "or open **System diagnostics** in the sidebar for local use."
    )

col1, col2 = st.columns(2)
with col1:
    st.subheader("Market & Signal Research")
    st.write("Analiza występowania modeli rynku i sygnałów oraz ich przyszłych rezultatów.")
    st.page_link(
        "pages/2_Market_and_Signal_Research.py",
        label="Open Market & Signal Research",
    )
with col2:
    st.subheader("Strategy Research")
    st.write("Wyniki backtestów, KPI, equity curve i wizualizacja transakcji na rynku.")
    st.page_link("pages/3_Strategy_Research.py", label="Open Strategy Research")

col3, col4 = st.columns(2)
with col3:
    st.subheader("Robustness Analysis")
    st.write("Walk-forward, parameter sweep, stress tests i Monte Carlo.")
    st.page_link("pages/4_Robustness_Analysis.py", label="Open Robustness Analysis")
with col4:
    st.subheader("Live Paper Trading")
    st.write("Bieżący stan instancji paper trading działającej na AWS.")
    st.page_link("pages/5_Live_Paper_Trading.py", label="Open Live Paper Trading")

st.divider()
st.page_link("pages/1_Research_Catalog.py", label="Browse Research Catalog")
