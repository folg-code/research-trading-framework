"""Project Overview copy and workflow diagrams."""

from __future__ import annotations

import streamlit as st

RESEARCH_WORKFLOW_MERMAID = """
flowchart LR
  provider[Data provider]
  normalize[Framework normalization]
  datasetRef[Normalized DatasetRef]
  models[Market and signal models]
  analysis[Research analysis]
  storage[Persisted research storage]
  analytics[Analytics layer / this dashboard]

  provider --> normalize --> datasetRef
  datasetRef --> models --> analysis --> storage --> analytics
"""

LIVE_WORKFLOW_MERMAID = """
flowchart TB
  subgraph research [Research path]
    strategySpec[Strategy model contract]
    backtest[Historical research runs]
    strategySpec --> backtest
  end

  subgraph aws [AWS live paper instance]
    runtime[Framework runtime]
    liveStrategy[Live strategy instance]
    runtime --> liveStrategy
  end

  strategySpec -. same contract — not the same instance .-> liveStrategy
  liveStrategy --> statusApi[Read-only status API]
  statusApi --> dashboard[Dashboard Live Paper view]
"""


def render_origin_of_results() -> None:
    """Render short explanation and research / live workflow diagrams."""
    st.subheader("Where results come from")
    st.markdown(
        "This dashboard is a **read-only analytics layer**. It does not run research "
        "engines or submit orders. It loads artifacts that the framework already "
        "produced and stored, plus a live paper status snapshot from AWS."
    )

    st.markdown("##### Research workflow")
    st.caption(
        "Provider data is normalized inside the framework. The resulting DatasetRef "
        "feeds market and signal models; research outputs are persisted to storage "
        "and then inspected here."
    )
    st.mermaid_chart(RESEARCH_WORKFLOW_MERMAID)

    st.markdown("##### Live paper workflow")
    st.caption(
        "A framework instance runs on AWS. Research and live paper share the same "
        "strategy **model contract**, but not the same strategy instance or "
        "parameters. The dashboard only consumes a read-only status view."
    )
    st.mermaid_chart(LIVE_WORKFLOW_MERMAID)


def render_module_cards() -> None:
    """Render the four module entry cards and catalog link."""
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Market & Signal Research")
        st.write(
            "Occurrence analysis for market and signal models, and how those "
            "events resolve afterward."
        )
        st.page_link(
            "pages/2_Market_and_Signal_Research.py",
            label="Open Market & Signal Research",
        )
    with col2:
        st.subheader("Strategy Research")
        st.write("Backtest results, KPIs, equity curves, and trade visualization on market data.")
        st.page_link("pages/3_Strategy_Research.py", label="Open Strategy Research")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Robustness Analysis")
        st.write("Walk-forward, parameter sweep, stress tests, and Monte Carlo.")
        st.page_link("pages/4_Robustness_Analysis.py", label="Open Robustness Analysis")
    with col4:
        st.subheader("Live Paper Trading")
        st.write("Current state of the AWS paper-trading instance.")
        st.page_link("pages/5_Live_Paper_Trading.py", label="Open Live Paper Trading")

    st.divider()
    st.page_link("pages/1_Research_Catalog.py", label="Browse Research Catalog")
