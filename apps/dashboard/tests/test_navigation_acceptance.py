"""Desktop acceptance render for the Signal Quality evidence path (Sprint 060 T004).

Mirrors ``test_overview_acceptance.py`` / ``test_study_acceptance.py``'s
convention: renders the real page files end to end via Streamlit's
``AppTest`` and asserts the PRD's navigation acceptance criteria that a
screenshot review alone cannot pin down as a repeatable regression check --
the study is reachable from the overview in no more than three navigation
actions, and methodology plus `Explore Evidence` are each one action from
the study (PRD-portfolio-dashboard-mvp.md).

``AppTest`` only fully resolves ``st.page_link`` targets (a real multipage
registry, keyed by the *root* script's directory) when the tree is entered
from the true entrypoint, ``Project_Overview.py`` -- loading a `pages/*.py`
file directly as if it were standalone breaks that registry (a Streamlit
testing-harness limitation, not a production behavior: a browser session
never opens a `pages/*.py` file directly either). ``AppTest.switch_page``
is the documented way to reach another page while keeping the real
registry, so every page below is reached that way rather than via
``AppTest.from_file("pages/...")`` directly.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from streamlit.testing.v1 import AppTest

#: Absolute, not "Project_Overview.py" -- AppTest.from_file resolves a
#: relative path against the current working directory first (falling back
#: to the calling test file's own directory), so a bare relative string
#: only works when pytest happens to be invoked from apps/dashboard. CI
#: invokes it from the repo root (`pytest apps/dashboard/tests -q`), where
#: neither resolution finds this file. `AppTest.switch_page` below still
#: resolves each `pages/...` target relative to this absolute path's own
#: parent directory, so it is unaffected by this change.
_PROJECT_OVERVIEW_PATH = str(Path(__file__).resolve().parents[1] / "Project_Overview.py")


@contextmanager
def _unconfigured_storage() -> Iterator[None]:
    with tempfile.TemporaryDirectory() as storage_root:
        os.environ["DASHBOARD_STORAGE_ROOT"] = storage_root
        try:
            yield
        finally:
            del os.environ["DASHBOARD_STORAGE_ROOT"]


def _run_overview() -> AppTest:
    with _unconfigured_storage():
        app = AppTest.from_file(_PROJECT_OVERVIEW_PATH)
        app.run(timeout=30)
    return app


def _switch_to(app: AppTest, page_path: str) -> AppTest:
    with _unconfigured_storage():
        app.switch_page(page_path)
        app.run(timeout=30)
    return app


def _page_link_targets(app: AppTest) -> set[str]:
    return {element.proto.page for element in app.get("page_link")}


def test_overview_links_to_the_workflow_context_page_in_one_action() -> None:
    app = _run_overview()

    assert not app.exception
    assert "Signal_Quality_Workflow" in _page_link_targets(app)


def test_workflow_context_page_renders_and_links_to_methodology_in_one_action() -> None:
    app = _switch_to(_run_overview(), "pages/13_Signal_Quality_Workflow.py")

    assert not app.exception
    assert app.title[0].value == "Signal Research and Predictive Research"
    assert "Signal_Quality_Methodology" in _page_link_targets(app)


def test_methodology_page_renders_and_links_to_the_study_in_one_action() -> None:
    app = _switch_to(_run_overview(), "pages/14_Signal_Quality_Methodology.py")

    assert not app.exception
    assert app.title[0].value == "Signal Quality Methodology"
    assert "Signal_Quality_Study" in _page_link_targets(app)


def test_study_page_renders_and_links_methodology_and_explore_evidence_in_one_action() -> None:
    app = _switch_to(_run_overview(), "pages/15_Signal_Quality_Study.py")

    assert not app.exception
    targets = _page_link_targets(app)
    assert "Signal_Quality_Methodology" in targets
    assert "Predictive_Research" in targets
    assert "Strategy_Research" in targets


def test_study_reachable_from_overview_in_no_more_than_three_navigation_actions() -> None:
    """Overview -> workflow context -> methodology -> study: three clicks."""
    overview = _run_overview()
    assert "Signal_Quality_Workflow" in _page_link_targets(overview)  # action 1

    workflow_context = _switch_to(overview, "pages/13_Signal_Quality_Workflow.py")
    assert "Signal_Quality_Methodology" in _page_link_targets(workflow_context)  # action 2

    methodology = _switch_to(overview, "pages/14_Signal_Quality_Methodology.py")
    assert "Signal_Quality_Study" in _page_link_targets(methodology)  # action 3
