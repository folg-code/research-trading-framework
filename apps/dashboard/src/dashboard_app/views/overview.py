"""Project Overview: product thesis, shared-domain map and workflow entries.

Sprint 059 T005 (ADR-0034): the thesis paragraph is the first real content
document loaded through the T004 content pipeline
(`dashboard_app.content.loader`); the shared-domain diagram and workflow
entry table are structural UI, not narrative, so they stay plain Python
data reusing existing enums (`WorkflowKind`, `StudyMaturity`) rather than a
second content document.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.manifest import StudyMaturity

ARCHITECTURE_ONE_PAGER_URL = "https://github.com/folg-code/research-trading-framework/blob/main/apps/dashboard/docs/ARCHITECTURE.md"

#: Hub-and-spoke, not a chain: every workflow node connects only to the
#: shared node, never to another workflow node. This is what makes "does
#: not depict one mandatory pipeline" (SPRINT_059.md acceptance criteria)
#: mechanically true rather than merely asserted in prose.
SHARED_DOMAIN_MERMAID = """
flowchart TB
  shared[Shared: Market Analysis, Time Model, Data Contracts]
  marketData[Market Data]
  signal[Signal Research]
  strategy[Strategy Research]
  robustness[Robustness Research]
  predictive[Predictive Research]
  execution[Strategy Execution]

  shared --> marketData
  shared --> signal
  shared --> strategy
  shared --> robustness
  shared --> predictive
  shared --> execution
"""

#: Wire values (StudyMaturity) -> the spaced display strings used
#: throughout the accepted product direction and PRD.
_MATURITY_DISPLAY: dict[StudyMaturity, str] = {
    StudyMaturity.AS_BUILT: "AS BUILT",
    StudyMaturity.IN_DEVELOPMENT: "IN DEVELOPMENT",
    StudyMaturity.FUTURE_IDEAS: "FUTURE IDEAS",
    StudyMaturity.ARCHIVED: "ARCHIVED",
}

_BadgeColor = Literal[
    "red", "orange", "yellow", "blue", "green", "violet", "gray", "grey", "primary"
]

#: Distinct `st.badge` colors per maturity so a future capability cannot be
#: mistaken for shipped capability (SPRINT_059.md acceptance criteria).
_MATURITY_BADGE_COLOR: dict[StudyMaturity, _BadgeColor] = {
    StudyMaturity.AS_BUILT: "green",
    StudyMaturity.IN_DEVELOPMENT: "blue",
    StudyMaturity.FUTURE_IDEAS: "gray",
    StudyMaturity.ARCHIVED: "red",
}


@dataclass(frozen=True, slots=True)
class WorkflowEntry:
    """One of the six independent workflows named in the accepted direction."""

    title: str
    workflow: WorkflowKind
    maturity: StudyMaturity
    page_path: str
    description: str


@dataclass(frozen=True, slots=True)
class PortfolioEntry:
    """One stable Home-page entry backed by reviewed content or evidence."""

    title: str
    page_path: str
    description: str


#: The six independent workflows (docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md
#: §3: "Market Data, Signal Research, Strategy Research, Robustness Research,
#: Predictive Research and Strategy Execution are separate workflows. Market
#: Analysis is a shared domain capability rather than a seventh workflow" --
#: Market Data is one of the six, NOT the shared capability; only Market
#: Analysis is shared). Market Data has no dedicated page today, so its entry
#: points at the same page as Signal Research; the card copy says so
#: explicitly rather than leaving the sharing implicit in a repeated
#: page_path. Strategy Execution is IN_DEVELOPMENT because
#: `pages/5_Live_Paper_Trading.py` is a dry-run monitor only (ADR-0021:
#: "Strategy Execution remains a future capability").
WORKFLOW_ENTRIES: tuple[WorkflowEntry, ...] = (
    WorkflowEntry(
        title="Market Data",
        workflow=WorkflowKind.MARKET,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/2_Market_and_Signal_Research.py",
        description=(
            "Provider ingestion, normalization and validation of market data used by "
            "every workflow below. Shares its page with Signal Research today."
        ),
    ),
    WorkflowEntry(
        title="Signal Research",
        workflow=WorkflowKind.SIGNAL,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/2_Market_and_Signal_Research.py",
        description="Occurrence analysis for market and signal models, and how events resolve.",
    ),
    WorkflowEntry(
        title="Strategy Research",
        workflow=WorkflowKind.STRATEGY,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/3_Strategy_Research.py",
        description="Backtest results, KPIs, equity curves, and trade visualization.",
    ),
    WorkflowEntry(
        title="Robustness Research",
        workflow=WorkflowKind.ROBUSTNESS,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/4_Robustness_Analysis.py",
        description="Walk-forward, parameter sweep, stress tests, and Monte Carlo.",
    ),
    WorkflowEntry(
        title="Predictive Research",
        workflow=WorkflowKind.PREDICTIVE,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/6_Predictive_Research.py",
        description="ML research diagnostics over persisted predictive runs and verdicts.",
    ),
    WorkflowEntry(
        title="Strategy Execution",
        workflow=WorkflowKind.LIVE_PAPER,
        maturity=StudyMaturity.IN_DEVELOPMENT,
        page_path="pages/5_Live_Paper_Trading.py",
        description="Paper-runtime observability today; live execution is a future capability.",
    ),
)

FEATURED_STUDIES: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="BTC Signal Quality Study",
        page_path="pages/9_BTC_Signal_Quality_Study.py",
        description=(
            "A persisted INCONCLUSIVE predictive verdict followed into a baseline-versus-"
            "score-filtered strategy comparison, including the negative downstream result."
        ),
    ),
    PortfolioEntry(
        title="Real-Data BTC Predictive Study",
        page_path="pages/6_Predictive_Research.py",
        description=(
            "A six-fold BTCUSDT.P study comparing linear, logistic and conditionally triggered "
            "tree evidence without turning a metric into trading approval."
        ),
    ),
)

RECENT_NOTES: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="Publishing evidence without publishing the workspace",
        page_path="pages/15_Research_and_Engineering_Notes.py",
        description="Why the public dashboard consumes an allowlisted projection.",
    ),
    PortfolioEntry(
        title="Why negative results stay visible",
        page_path="pages/15_Research_and_Engineering_Notes.py",
        description="What the BTC studies demonstrate about stopping rules and honest reporting.",
    ),
    PortfolioEntry(
        title="Live data is not live trading",
        page_path="pages/15_Research_and_Engineering_Notes.py",
        description="How the dry-run boundary separates market observation from real orders.",
    ),
)

FUTURE_IDEAS: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="AI Research Infrastructure",
        page_path="pages/13_AI_Research_Infrastructure.py",
        description=(
            "A proposed AI control plane over deterministic research compute, with explicit "
            "roles, budgets and anti-data-mining guardrails."
        ),
    ),
    PortfolioEntry(
        title="Research Application",
        page_path="pages/14_Research_Application.py",
        description=(
            "A draft local-first Workbench direction that coordinates existing workflows "
            "without becoming a second research engine."
        ),
    ),
)


def render_product_thesis() -> None:
    """Render the version-controlled overview thesis (ADR-0034 content pipeline).

    Fails closed: an absent or invalid content document shows an explicit
    warning, never a raised exception or partially-rendered page.
    """
    document = load_content_document(content_document_path("portfolio-overview"))
    if isinstance(document, ContentUnavailable):
        st.warning(f"Overview content unavailable ({document.reason}): {document.detail}")
        return

    st.markdown(document.body_markdown)


def render_shared_domain_map() -> None:
    """Render the hub-and-spoke shared-domain diagram."""
    st.subheader("Shared domain, independent workflows")
    st.caption(
        "Every workflow below reads the same shared market-data, market-analysis "
        "and time-model contracts, but none of them requires another to have run "
        "first. This is a simplified map — see the "
        f"[architecture one-pager]({ARCHITECTURE_ONE_PAGER_URL}) for the full picture."
    )
    st.mermaid_chart(SHARED_DOMAIN_MERMAID)
    st.page_link("pages/10_Architecture.py", label="Explore Architecture")


def render_workflow_entries() -> None:
    """Render the six workflow entry cards, each with a maturity badge."""
    for row_start in range(0, len(WORKFLOW_ENTRIES), 2):
        columns = st.columns(2)
        for entry, column in zip(
            WORKFLOW_ENTRIES[row_start : row_start + 2], columns, strict=False
        ):
            with column:
                st.subheader(entry.title)
                st.badge(
                    _MATURITY_DISPLAY[entry.maturity],
                    color=_MATURITY_BADGE_COLOR[entry.maturity],
                )
                st.write(entry.description)
                st.page_link(entry.page_path, label=f"Open {entry.title}")


def _render_portfolio_entries(entries: tuple[PortfolioEntry, ...]) -> None:
    columns = st.columns(len(entries))
    for entry, column in zip(entries, columns, strict=True):
        with column:
            st.subheader(entry.title)
            st.write(entry.description)
            st.page_link(entry.page_path, label=f"Open {entry.title}")


def render_featured_studies() -> None:
    """Render two reviewed, real-evidence study entry points."""
    st.header("Featured studies")
    st.caption("Persisted evidence, including results that did not support the hypothesis.")
    _render_portfolio_entries(FEATURED_STUDIES)


def render_recent_notes() -> None:
    """Render the three selected Research & Engineering Note entries."""
    st.header("Research & Engineering Notes")
    _render_portfolio_entries(RECENT_NOTES)
    st.page_link("pages/11_Engineering.py", label="Explore Engineering")


def render_future_ideas() -> None:
    """Render exactly the two maintainer-approved Future Ideas cards."""
    st.header("Future direction")
    columns = st.columns(len(FUTURE_IDEAS))
    for entry, column in zip(FUTURE_IDEAS, columns, strict=True):
        with column:
            st.subheader(entry.title)
            st.badge("FUTURE IDEAS", color="gray")
            st.write(entry.description)
            st.page_link(entry.page_path, label=f"Explore {entry.title}")
    st.page_link("pages/12_Future_Direction.py", label="Open Future Direction")


def render_catalog_entry() -> None:
    """Keep the complete catalog as the final Home information block."""
    st.header("Complete research catalog")
    st.caption(
        "Inspect the available persisted results. Catalog migration to the sanitized public "
        "projection is in development during Sprint 061."
    )
    st.page_link("pages/1_Research_Catalog.py", label="Browse Research Catalog")
