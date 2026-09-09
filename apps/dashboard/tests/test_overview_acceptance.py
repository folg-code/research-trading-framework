"""Desktop acceptance render for the portfolio overview (Sprint 059 T006).

Renders `Project_Overview.py` end to end via Streamlit's `AppTest` --
the actual script execution, not just a static read of its source -- and
asserts the accepted-direction acceptance criteria that a screenshot
review alone cannot pin down as a repeatable regression check: no
exception, the thesis is readable before any workflow detail, all six
workflows are named with a maturity badge, and the shared-domain diagram
is a star (never a mandatory pipeline). A real desktop-viewport screenshot
was additionally reviewed by hand as part of this sprint's closeout (see
SPRINT_059.md `## Closeout`); this test is the durable, automated half of
that acceptance check.
"""

from __future__ import annotations

import os
import re
import tempfile

from streamlit.testing.v1 import AppTest

from dashboard_app.views.overview import WORKFLOW_ENTRIES

_BADGE_PATTERN = re.compile(r":(\w+)-badge\[([^\]]+)\]")


def _run_overview_app() -> AppTest:
    with tempfile.TemporaryDirectory() as storage_root:
        os.environ["DASHBOARD_STORAGE_ROOT"] = storage_root
        try:
            app = AppTest.from_file("Project_Overview.py")
            app.run(timeout=30)
        finally:
            del os.environ["DASHBOARD_STORAGE_ROOT"]
    return app


def test_overview_renders_without_exception() -> None:
    app = _run_overview_app()

    assert not app.exception


def test_overview_title_and_thesis_render_before_workflow_detail() -> None:
    app = _run_overview_app()

    assert app.title[0].value == "Trading Research Framework"
    thesis_markdown = app.markdown[0].value
    assert "read-only" in thesis_markdown.lower()
    assert "github.com/folg-code/research-trading-framework" in thesis_markdown

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
    badge_labels = {label for _color, label in badges}
    assert badge_labels == {"AS BUILT", "IN DEVELOPMENT"}
    assert len(badges) == len(WORKFLOW_ENTRIES)


def test_overview_shared_domain_diagram_is_a_star_not_a_chain() -> None:
    app = _run_overview_app()

    diagram_markdown = next(entry.value for entry in app.markdown if "flowchart" in entry.value)
    edge_lines = [line.strip() for line in diagram_markdown.splitlines() if "-->" in line]
    assert edge_lines, "expected the rendered diagram to contain edges"
    for line in edge_lines:
        source, _, _target = line.partition("-->")
        assert source.strip() == "shared", f"unexpected edge source in rendered diagram: {line!r}"


def test_overview_does_not_render_legacy_linear_pipeline_language() -> None:
    app = _run_overview_app()

    full_text = "\n".join(entry.value for entry in app.markdown)
    assert "Data provider" not in full_text
    assert "Framework normalization" not in full_text
    # The page explicitly denies being a mandatory pipeline; it must not
    # ALSO assert the positive framing anywhere.
    assert "not one mandatory pipeline" in full_text.lower()
    assert re.search(r"(?<!not )one mandatory pipeline", full_text.lower()) is None
