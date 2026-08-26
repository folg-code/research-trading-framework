"""Tests for Predictive Research offline HTML assembly."""

from __future__ import annotations

from pathlib import Path

from tests.unit.research.reporting.predictive.test_view_model import (
    _GENERATED,
    _source_report,
)
from trading_framework.research.reporting.predictive.panels import (
    PREDICTIVE_REPORT_PANELS,
    PanelStatus,
    resolve_report_panels,
)
from trading_framework.research.reporting.predictive.report_html import (
    PANEL_BODY_RENDERERS,
    render_predictive_research_report_html,
)
from trading_framework.research.reporting.predictive.view_models import (
    PredictiveReportViewModel,
    build_predictive_report_view_model,
)
from trading_framework.time.clocks.fixed import FixedClock


def _view(*, binary: bool = False, with_proba: bool = False) -> PredictiveReportViewModel:
    return build_predictive_report_view_model(
        _source_report(binary=binary, with_proba=with_proba),
        clock=FixedClock(_GENERATED),
    )


def test_every_registered_panel_has_a_body_renderer() -> None:
    assert {definition.panel_id for definition in PREDICTIVE_REPORT_PANELS} == set(
        PANEL_BODY_RENDERERS
    )


def test_html_is_offline_and_embeds_plotly_without_cdn(tmp_path: Path) -> None:
    output = tmp_path / "report.html"
    render_predictive_research_report_html(_view(), output)
    document = output.read_text(encoding="utf-8")
    assert 'src="https://cdn.plot.ly' not in document
    assert "include_plotlyjs" not in document
    assert "include_plotlyjs" not in document
    assert document.count("plotly-graph-div") >= 1
    assert "Fold timeline" in document
    assert "A thin purge band" in document
    assert "Quality flags" in document


def test_classification_without_probabilities_skips_calibration_with_note(
    tmp_path: Path,
) -> None:
    view = _view(binary=True, with_proba=False)
    resolved = {panel.panel_id: panel for panel in resolve_report_panels(view)}
    assert resolved["calibration"].status is PanelStatus.SKIP
    output = tmp_path / "classification.html"
    render_predictive_research_report_html(view, output)
    document = output.read_text(encoding="utf-8")
    assert "probabilities" in document
    assert 'id="calibration"' in document
    assert "Skipped" in document
    assert "SMALL_TEST_SAMPLE" in document
    assert "threshold=" in document
