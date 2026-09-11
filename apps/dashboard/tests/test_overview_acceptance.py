"""Desktop acceptance render for the portfolio overview (Sprint 059 T006).

Renders `Project_Overview.py` end to end via Streamlit's `AppTest` --
the actual script execution, not just a static read of its source -- and
asserts the accepted-direction acceptance criteria that a screenshot
review alone cannot pin down as a repeatable regression check: no
exception, the thesis is readable before any workflow detail, all six
workflows are named with a maturity badge, and the architecture diagram
keeps data preparation, shared composition and workflow-owned evidence
separate. A real desktop-viewport screenshot
was additionally reviewed by hand as part of this sprint's closeout (see
SPRINT_059.md `## Closeout`); this test is the durable, automated half of
that acceptance check.
"""

from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard_app.views.overview import WORKFLOW_ENTRIES

_BADGE_PATTERN = re.compile(r":(\w+)-badge\[([^\]]+)\]")

#: Absolute, not "Project_Overview.py" -- AppTest.from_file resolves a
#: relative path against the current working directory first (falling back
#: to the calling test file's own directory), so a bare relative string
#: only works when pytest happens to be invoked from apps/dashboard. CI
#: invokes it from the repo root (`pytest apps/dashboard/tests -q`), where
#: neither resolution finds this file.
_PROJECT_OVERVIEW_PATH = str(Path(__file__).resolve().parents[1] / "Project_Overview.py")


def _run_overview_app() -> AppTest:
    app = AppTest.from_file(_PROJECT_OVERVIEW_PATH)
    app.run(timeout=30)
    return app


def test_overview_renders_without_exception() -> None:
    app = _run_overview_app()

    assert not app.exception
    assert not app.warning
    assert not app.error
    assert not app.text_input


def test_overview_title_and_thesis_render_before_workflow_detail() -> None:
    app = _run_overview_app()

    assert app.title[0].value == "Trading Research Framework"
    # The dense architecture narrative (DAG, DatasetRef, timing rules) lives
    # in a collapsed expander so the landing view isn't a wall of text; the
    # jargon-light lead and the linked detail can land in different
    # markdown blocks, so check presence across all of them rather than
    # requiring both substrings in one block.
    all_markdown_text = "\n".join(block.value for block in app.markdown)
    assert "read-only" in all_markdown_text.lower()
    assert "github.com/folg-code/research-trading-framework" in all_markdown_text

    # Top-level page order (title -> thesis -> ... -> shared-domain map ->
    # workflow cards): the thesis markdown block must render before the
    # first top-level subheader, proving the thesis leads, not trails.
    ordered_types = [child.type for child in app.main.children.values()]
    first_markdown_index = ordered_types.index("markdown")
    first_subheader_index = ordered_types.index("subheader")
    assert first_markdown_index < first_subheader_index


def test_overview_names_all_six_workflows_with_maturity_badges() -> None:
    app = _run_overview_app()

    rendered_subheaders = {entry.value for entry in app.subheader}
    for entry in WORKFLOW_ENTRIES:
        assert entry.title in rendered_subheaders

    badges = [
        match.groups()
        for markdown_element in app.markdown
        for match in _BADGE_PATTERN.finditer(markdown_element.value)
    ]
    workflow_badges = badges[: len(WORKFLOW_ENTRIES)]
    badge_labels = {label for _color, label in workflow_badges}
    assert badge_labels == {"AS BUILT", "IN DEVELOPMENT"}
    assert len(workflow_badges) == len(WORKFLOW_ENTRIES)


def test_overview_diagram_preserves_modular_boundaries_and_composition() -> None:
    app = _run_overview_app()

    diagram_markdown = next(entry.value for entry in app.markdown if "flowchart" in entry.value)
    for label in (
        "Provider adapters",
        "Published DatasetRef",
        "Market Model",
        "Signal Model",
        "Exit Model",
        "Risk Model",
        "Strategy Model: Market x Signal x Exit x Risk",
        "Workflow-owned persisted evidence",
    ):
        assert label in diagram_markdown

    assert "preparation --> dataset" in diagram_markdown
    assert "dataset --> analysis" in diagram_markdown
    assert "market --> strategyModel" in diagram_markdown
    assert "signalModel --> strategyModel" in diagram_markdown
    assert "exit --> strategyModel" in diagram_markdown
    assert "risk --> strategyModel" in diagram_markdown

    # Market Data owns preparation and publication only. Each downstream
    # result is produced by its named research or execution workflow.
    market_data_block = diagram_markdown.split("subgraph marketData", maxsplit=1)[1].split(
        "end", maxsplit=1
    )[0]
    assert "Research" not in market_data_block
    assert "result" not in market_data_block.lower()
    assert "signalResearch --> signalEvidence" in diagram_markdown
    assert "predictive --> predictiveEvidence" in diagram_markdown
    assert "strategyResearch --> strategyEvidence" in diagram_markdown


def test_overview_does_not_render_legacy_linear_pipeline_language() -> None:
    app = _run_overview_app()

    full_text = "\n".join(
        [entry.value for entry in app.markdown] + [entry.value for entry in app.caption]
    )
    assert "Data provider" not in full_text
    assert "Framework normalization" not in full_text
    # The page explicitly denies being a mandatory pipeline; it must not
    # ALSO assert the positive framing anywhere.
    assert "not one mandatory pipeline" in full_text.lower()
    assert re.search(r"(?<!not )one mandatory pipeline", full_text.lower()) is None


def test_overview_explains_btc_is_an_evidence_choice_not_an_asset_boundary() -> None:
    app = _run_overview_app()

    full_text = "\n".join(
        [entry.value for entry in app.markdown] + [entry.value for entry in app.caption]
    )
    assert "free public API" in full_text
    assert "not a framework boundary" in full_text
    assert "published as a DatasetRef" in full_text
