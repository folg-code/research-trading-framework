"""Tests for Sprint 043 Predictive Research report panels."""

from __future__ import annotations

from pathlib import Path

from tests.unit.research.reporting.predictive.test_view_model import (
    _GENERATED,
    _learning_curves,
    _source_report,
    _window_accounting,
)
from trading_framework.research.reporting.predictive.plotly_figures import (
    build_learning_curves_figure,
    build_window_accounting_figure,
    require_plotly,
)
from trading_framework.research.reporting.predictive.report_html import (
    render_predictive_research_report_html,
)
from trading_framework.research.reporting.predictive.view_models import (
    PredictiveReportViewModel,
    build_predictive_report_view_model,
)
from trading_framework.time.clocks.fixed import FixedClock


def _neural_view() -> PredictiveReportViewModel:
    return build_predictive_report_view_model(
        _source_report(
            learning_curves=_learning_curves(),
            window_accounting=_window_accounting(),
        ),
        clock=FixedClock(_GENERATED),
    )


def test_learning_curves_figure_marks_stopping_epoch() -> None:
    go, _pio, _make_subplots = require_plotly()
    figure = build_learning_curves_figure(go, _neural_view())
    names = [str(trace.name) for trace in figure.data]
    assert "Fold 0 train" in names
    assert "Fold 0 validation" in names
    assert "Fold 0 stop" in names
    stop = next(trace for trace in figure.data if trace.name == "Fold 0 stop")
    assert list(stop.x) == [3]
    assert list(stop.y) == [0.55]


def test_window_accounting_figure_stacks_dropped_and_effective_sample() -> None:
    go, _pio, _make_subplots = require_plotly()
    figure = build_window_accounting_figure(go, _neural_view())
    names = [str(trace.name) for trace in figure.data]
    assert names == [
        "Effective sample",
        "Dropped incomplete",
        "Dropped gap",
        "Dropped fold boundary",
    ]
    labels = list(figure.data[0].x)
    assert labels[0] == "Fold 0 TRAIN"
    assert labels[1] == "Fold 0 TEST"
    assert list(figure.data[0].y) == [12, 6]


def test_html_renders_neural_panels_when_sidecars_are_present(tmp_path: Path) -> None:
    output = tmp_path / "neural-report.html"
    render_predictive_research_report_html(_neural_view(), output)
    document = output.read_text(encoding="utf-8")
    assert 'id="learning_curves"' in document
    assert 'id="window_accounting"' in document
    assert "inner early-stopping run" in document
    start = document.index('id="learning_curves"')
    end = document.find("<section", start + 1)
    assert "chart-block" in document[start:end]
    assert "Skipped" not in document[start:end]
    accounting_start = document.index('id="window_accounting"')
    accounting_end = document.find("<section", accounting_start + 1)
    if accounting_end == -1:
        accounting_end = len(document)
    assert "chart-block" in document[accounting_start:accounting_end]
    assert "Skipped" not in document[accounting_start:accounting_end]
