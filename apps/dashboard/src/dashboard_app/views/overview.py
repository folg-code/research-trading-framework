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

#: Market Data ends at a published DatasetRef. Research and execution are
#: independent consumers of shared contracts; each workflow owns its outputs.
#: Strategy composition is explicit rather than hidden in a monolithic class.
SHARED_DOMAIN_MERMAID = """
flowchart LR
  subgraph providers[Provider boundary]
    sources[OHLCV sources: APIs, archives, files]
    adapters[Provider adapters]
  end

  subgraph marketData[Market Data workflow]
    preparation[Normalize, validate, version]
    dataset[Published DatasetRef]
  end

  sources --> adapters --> preparation --> dataset

  subgraph shared[Shared domain contracts]
    analysis[Market Analysis: Features, Structures, States]
    market[Market Model]
    signalModel[Signal Model]
    exit[Exit Model]
    risk[Risk Model]
    strategyModel[Strategy Model: Market x Signal x Exit x Risk]
    analysis --> market
    analysis --> signalModel
    market --> strategyModel
    signalModel --> strategyModel
    exit --> strategyModel
    risk --> strategyModel
  end

  dataset --> analysis

  subgraph workflows[Independent workflow consumers]
    signalResearch[Signal Research]
    strategyResearch[Strategy Research]
    robustness[Robustness Research]
    predictive[Predictive Research]
    execution[Strategy Execution: DRY_RUN today]
  end

  dataset --> signalResearch
  market --> signalResearch
  signalModel --> signalResearch
  dataset --> predictive
  analysis --> predictive
  dataset --> strategyResearch
  strategyModel --> strategyResearch
  strategyModel --> robustness
  strategyModel --> execution

  subgraph evidence[Workflow-owned persisted evidence]
    signalEvidence[Signal Research Dataset]
    predictiveEvidence[Predictive Dataset, Run, Verdict]
    strategyEvidence[Strategy Research Dataset]
    robustnessEvidence[Robustness artifacts]
    executionState[Operational state]
  end

  signalResearch --> signalEvidence
  predictive --> predictiveEvidence
  strategyResearch --> strategyEvidence
  robustness --> robustnessEvidence
  execution --> executionState
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
#: Analysis is shared). Each entry leads to a methodology/architecture
#: publication before offering a link to technical evidence. Strategy
#: Execution is IN_DEVELOPMENT because
#: `pages/12_Live_Paper_Trading.py` is a dry-run monitor only (ADR-0021:
#: "Strategy Execution remains a future capability").
WORKFLOW_ENTRIES: tuple[WorkflowEntry, ...] = (
    WorkflowEntry(
        title="Market Data",
        workflow=WorkflowKind.MARKET,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/2_Market_Data_Workflow.py",
        description=(
            "Provider adapters turn OHLCV from APIs, archives or files into validated, "
            "versioned DatasetRefs. This workflow prepares inputs; it does not produce "
            "research results."
        ),
    ),
    WorkflowEntry(
        title="Signal Research",
        workflow=WorkflowKind.SIGNAL,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/3_Signal_Research_Workflow.py",
        description=(
            "Methodology for Market Models, Signal Models or their composition, with "
            "persistent occurrence and forward-outcome evidence."
        ),
    ),
    WorkflowEntry(
        title="Strategy Research",
        workflow=WorkflowKind.STRATEGY,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/5_Strategy_Research_Workflow.py",
        description=(
            "Methodology for complete Market x Signal x Exit x Risk compositions under "
            "explicit historical and execution assumptions."
        ),
    ),
    WorkflowEntry(
        title="Robustness Research",
        workflow=WorkflowKind.ROBUSTNESS,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/7_Robustness_Research_Workflow.py",
        description=(
            "Methodology for challenging persisted strategy evidence with walk-forward, "
            "parameter, stress and Monte Carlo tests."
        ),
    ),
    WorkflowEntry(
        title="Predictive Research",
        workflow=WorkflowKind.PREDICTIVE,
        maturity=StudyMaturity.AS_BUILT,
        page_path="pages/9_Predictive_Research_Workflow.py",
        description=(
            "Leakage-aware methodology for testing whether analysis columns contain "
            "out-of-sample predictive information."
        ),
    ),
    WorkflowEntry(
        title="Strategy Execution",
        workflow=WorkflowKind.LIVE_PAPER,
        maturity=StudyMaturity.IN_DEVELOPMENT,
        page_path="pages/11_Strategy_Execution_Workflow.py",
        description=(
            "Architecture for applying the same Strategy Model definitions to runtime data. "
            "Only simulated DRY_RUN execution is available today."
        ),
    ),
)

FEATURED_STUDIES: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="Signal Quality Study",
        page_path="pages/15_Signal_Quality_Study.py",
        description=(
            "A persisted INCONCLUSIVE predictive verdict followed into a baseline-versus-"
            "score-filtered strategy comparison, including the negative downstream result."
        ),
    ),
    PortfolioEntry(
        title="Predictive Model Benchmark",
        page_path="pages/10_Predictive_Research.py",
        description=(
            "A real-data benchmark comparing linear, logistic and conditionally triggered "
            "tree evidence across temporal folds. BTCUSDT.P is the selected dataset, not "
            "the scope of the method."
        ),
    ),
)

RECENT_NOTES: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="Publishing evidence without publishing the workspace",
        page_path="pages/21_Research_and_Engineering_Notes.py",
        description="Why the public dashboard consumes an allowlisted projection.",
    ),
    PortfolioEntry(
        title="Why negative results stay visible",
        page_path="pages/21_Research_and_Engineering_Notes.py",
        description="What the BTC studies demonstrate about stopping rules and honest reporting.",
    ),
    PortfolioEntry(
        title="Live data is not live trading",
        page_path="pages/21_Research_and_Engineering_Notes.py",
        description="How the dry-run boundary separates market observation from real orders.",
    ),
)

FUTURE_IDEAS: tuple[PortfolioEntry, ...] = (
    PortfolioEntry(
        title="AI Research Infrastructure",
        page_path="pages/19_AI_Research_Infrastructure.py",
        description=(
            "A proposed AI control plane over deterministic research compute, with explicit "
            "roles, budgets and anti-data-mining guardrails."
        ),
    ),
    PortfolioEntry(
        title="Research Application",
        page_path="pages/20_Research_Application.py",
        description=(
            "A draft local-first Workbench direction that coordinates existing workflows "
            "without becoming a second research engine."
        ),
    ),
)


AUTHOR_NAME = "Filip Folga"
AUTHOR_LINKEDIN_URL = "https://www.linkedin.com/in/filip-folga/"
AUTHOR_EMAIL = "filip1folga@gmail.com"

AUTHOR_SUMMARY = (
    "Python engineer with commercial experience building backend services, REST "
    "APIs and database-driven applications with Django, PostgreSQL and Redis, "
    "including external API integration, time-series data processing, automated "
    "testing and CI/CD-based deployment of containerized services. This dashboard "
    "is the public projection of an independently built quantitative research "
    "framework applying that same discipline — versioned data contracts, "
    "reproducible pipelines, evidence kept even when a result is negative — to "
    "market data, chosen here for its data availability rather than as a trading "
    "product."
)


def render_author_intro() -> None:
    """Render a short author identity block so the project is attributable.

    Recruiter feedback on the public dashboard: the project reads as a
    system, but nothing on it says who built it or how to reach them.
    """
    st.caption(
        "TL;DR: a reproducible research system that turns time-indexed market "
        "data into inspectable evidence — built solo, with results kept visible "
        "even when they are negative."
    )
    with st.container(border=True):
        st.markdown(f"**{AUTHOR_NAME}** — Python / Data Engineer")
        st.write(AUTHOR_SUMMARY)
        st.markdown(f"[LinkedIn]({AUTHOR_LINKEDIN_URL}) · [Email](mailto:{AUTHOR_EMAIL})")


#: The lead (everything above the first `## ` heading) is jargon-light and
#: meant to be read in full on landing; the rest is the denser architecture
#: narrative (DAG, temporal-correctness rules, DatasetRef mechanics) that a
#: recruiter or engineer unfamiliar with trading can skip without missing
#: what the project is or who built it. Collapsing it behind an expander
#: (Sprint feedback: the overview read as a "wall of text" on first load)
#: keeps that detail one click away instead of removed.
_THESIS_HEADING_MARKER = "\n## "


def render_product_thesis() -> None:
    """Render the version-controlled overview thesis (ADR-0034 content pipeline).

    Fails closed: an absent or invalid content document shows an explicit
    warning, never a raised exception or partially-rendered page.
    """
    document = load_content_document(content_document_path("portfolio-overview"))
    if isinstance(document, ContentUnavailable):
        st.warning(f"Overview content unavailable ({document.reason}): {document.detail}")
        return

    body = document.body_markdown
    split_index = body.find(_THESIS_HEADING_MARKER)
    if split_index == -1:
        st.markdown(body)
        return

    st.markdown(body[:split_index])
    detail_body = body[split_index:].lstrip("\n")
    _, _, detail_body = detail_body.partition("\n")  # drop the redundant "## ..." heading line
    with st.expander("How it works under the hood (architecture, data pipeline, timing rules)"):
        st.markdown(detail_body.lstrip("\n"))


def render_shared_domain_map() -> None:
    """Render the provider-neutral data boundary and compositional architecture."""
    st.subheader("Modular infrastructure, shared contracts")
    st.caption(
        "Provider adapters converge on one published DatasetRef contract. Research "
        "workflows reuse data and model identities without sharing mandatory workflow "
        "state, while each workflow persists its own evidence. A Strategy Model is the "
        "explicit composition Market x Signal x Exit x Risk. See the "
        f"[architecture one-pager]({ARCHITECTURE_ONE_PAGER_URL}) for repository detail."
    )
    st.mermaid_chart(SHARED_DOMAIN_MERMAID)
    st.page_link("pages/16_Architecture.py", label="Explore Architecture")


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
    st.caption(
        "BTCUSDT.P is the development asset because crypto exchanges — Binance in "
        "particular — provide the most practical access to high-quality historical OHLCV "
        "through a free public API. It is not a framework boundary: adapter and repository "
        "patterns let another provider and asset use the same contracts after normalization "
        "and publication as a DatasetRef."
    )
    _render_portfolio_entries(FEATURED_STUDIES)


def render_recent_notes() -> None:
    """Render the three selected Research & Engineering Note entries."""
    st.header("Research & Engineering Notes")
    _render_portfolio_entries(RECENT_NOTES)
    st.page_link("pages/17_Engineering.py", label="Explore Engineering")


def render_future_ideas() -> None:
    """Render exactly the two maintainer-approved Future Ideas cards."""
    st.header("Future direction")
    columns = st.columns(len(FUTURE_IDEAS))
    for entry, column in zip(FUTURE_IDEAS, columns, strict=True):
        with column:
            st.subheader(entry.title)
            st.badge("FUTURE IDEAS", color="violet")
            st.write(entry.description)
            st.page_link(entry.page_path, label=f"Explore {entry.title}")
    st.page_link("pages/18_Future_Direction.py", label="Open Future Direction")


def render_catalog_entry() -> None:
    """Keep the complete catalog as the final Home information block."""
    st.header("Complete research catalog")
    st.caption(
        "Inspect every safely identifiable result in the immutable public projection, grouped "
        "as study → experiment → run without exposing the private research workspace."
    )
    st.page_link("pages/1_Research_Catalog.py", label="Browse Research Catalog")
