"""Project Overview copy and workflow diagrams."""

from __future__ import annotations

import streamlit as st

ARCHITECTURE_ONE_PAGER_URL = "https://github.com/folg-code/research-trading-framework/blob/main/apps/dashboard/docs/ARCHITECTURE.md"

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
flowchart LR
  exchange[Exchange provider live feed]
  subgraph aws [AWS]
    runtime[Framework runtime]
    strategy[Live strategy instance]
    runtime --> strategy
  end
  statusApi[Read-only status API]
  dashboard[Dashboard Live Paper view]

  exchange --> runtime
  strategy --> statusApi --> dashboard
"""

CAPABILITIES_MERMAID = """
flowchart TB
  shared[Shared definitions: market, models, time, data]
  signal[Signal Research]
  strategy[Strategy Research]
  execution[Strategy Execution]

  shared --> signal
  shared --> strategy
  shared --> execution
"""


def render_origin_of_results() -> None:
    """Render short explanation and research / live workflow diagrams."""
    st.subheader("Where results come from")
    st.markdown(
        "This dashboard is a **read-only analytics layer**. It does not run research "
        "engines or submit orders. It loads artifacts that the framework already "
        "produced and stored, plus a live paper status snapshot from AWS."
    )
    st.caption(
        "The diagrams below are a **simplified** view of the end-to-end workflow. "
        f"For a short public architecture map, see the "
        f"[architecture one-pager]({ARCHITECTURE_ONE_PAGER_URL}). "
        "Module contracts and methodology detail live in the "
        "[project README on GitHub](https://github.com/folg-code/research-trading-framework)."
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
        "On AWS the framework runtime and live strategy instance run together. "
        "The runtime listens to **real market data** from the exchange provider; "
        "the strategy (same model contract as research, not the same instance) "
        "runs paper simulation only. This dashboard consumes a read-only status "
        "view — it never submits orders."
    )
    st.mermaid_chart(LIVE_WORKFLOW_MERMAID)


def render_architecture_one_pager() -> None:
    """Render a short in-app architecture summary with link to the full one-pager."""
    st.subheader("Architecture at a glance")
    st.markdown(
        """
Signal, strategy, and execution are **independent capabilities** that share contracts —
not stages of one mandatory pipeline. Framework code stays in `src/`; datasets and runs
stay in user space. This dashboard only reads persisted research and a read-only live
status API.
"""
    )
    st.mermaid_chart(CAPABILITIES_MERMAID)
    st.markdown(
        f"Full one-pager (boundaries, live-paper path, links): "
        f"[apps/dashboard/docs/ARCHITECTURE.md]({ARCHITECTURE_ONE_PAGER_URL})"
    )


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
