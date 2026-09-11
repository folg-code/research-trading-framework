"""Desktop acceptance render for the BTC Signal Quality study (Sprint 060 T003).

Mirrors ``test_overview_acceptance.py``'s convention: renders the actual
view function end to end via Streamlit's ``AppTest`` and asserts the
acceptance-relevant properties a unit test on the pure helpers cannot pin
down -- no exception, the persisted verdict appears verbatim, all three
charts render, and no dashboard-computed conclusion leaks in anywhere the
view's own copy text can be inspected.
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

from streamlit.testing.v1 import AppTest

_APP_SCRIPT = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, {src!r})
    from dashboard_app.views.study import render_btc_signal_quality_study
    render_btc_signal_quality_study()
    """
)


def _run_study_app() -> AppTest:
    dashboard_src = str(Path(__file__).resolve().parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "study_smoke_app.py"
        script_path.write_text(_APP_SCRIPT.format(src=dashboard_src), encoding="utf-8")

        app = AppTest.from_file(str(script_path))
        app.run(timeout=30)
        return app


def test_study_renders_without_exception() -> None:
    app = _run_study_app()

    assert not app.exception


def test_study_shows_the_persisted_verdict_verbatim() -> None:
    app = _run_study_app()

    assert app.title[0].value == "Signal Quality Study"
    badge_markdown = "\n".join(entry.value for entry in app.markdown)
    assert ":gray-badge[INCONCLUSIVE]" in badge_markdown


def test_study_renders_all_three_charts() -> None:
    app = _run_study_app()

    subheaders = {entry.value for entry in app.subheader}
    assert "Model vs. random-permutation ROC AUC" in subheaders
    assert "Threshold sensitivity" in subheaders
    assert "Baseline vs. scored trade disposition" in subheaders
    assert len(app.get("plotly_chart")) == 3


def test_study_content_and_view_never_state_a_new_conclusion() -> None:
    """Neither the content prose nor the view's own captions may draw a
    conclusion beyond what the persisted verdict and charts already show."""
    app = _run_study_app()

    full_text = "\n".join(entry.value for entry in app.markdown).lower()
    full_text += "\n".join(entry.value for entry in app.caption).lower()
    for banned_phrase in ("we conclude", "this proves", "therefore the strategy", "confirms that"):
        assert banned_phrase not in full_text
