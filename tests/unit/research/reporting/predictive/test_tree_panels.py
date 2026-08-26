"""Tests for Sprint 042 Predictive Research report panels."""

from __future__ import annotations

from pathlib import Path

from tests.unit.research.reporting.predictive.test_view_model import (
    _GENERATED,
    _importance_trace,
    _leaderboard,
    _selection_trace,
    _source_report,
)
from trading_framework.research.reporting.predictive.plotly_figures import (
    build_feature_importance_figure,
    build_leaderboard_figure,
    build_selection_trace_figure,
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


def _tree_view(*, native: bool = True) -> PredictiveReportViewModel:
    return build_predictive_report_view_model(
        _source_report(
            importance=_importance_trace(native=native),
            selection=_selection_trace(),
            leaderboard=_leaderboard(),
            fold_primary={
                "0": {"train_primary": 0.9, "test_primary": 0.4, "primary_gap": 0.5},
            },
        ),
        clock=FixedClock(_GENERATED),
    )


def test_feature_importance_figure_is_side_by_side_native_and_permutation() -> None:
    go, _pio, make_subplots = require_plotly()
    figure = build_feature_importance_figure(go, make_subplots, _tree_view())
    names = [str(trace.name) for trace in figure.data]
    assert "Native gain" in names
    assert "Permutation" in names
    permutation = next(trace for trace in figure.data if trace.name == "Permutation")
    assert list(permutation.x) == ["signal", "noise"]


def test_feature_importance_figure_annotates_missing_native_scores() -> None:
    go, _pio, make_subplots = require_plotly()
    figure = build_feature_importance_figure(go, make_subplots, _tree_view(native=False))
    texts = [str(annotation.text) for annotation in figure.layout.annotations]
    assert any("unavailable" in text.lower() for text in texts)


def test_leaderboard_figure_ranks_families_ahead_of_baselines() -> None:
    go, _pio, _make_subplots = require_plotly()
    figure = build_leaderboard_figure(go, _tree_view())
    labels = list(figure.data[0].y)
    assert labels[-1].startswith("xgboost.regressor")
    assert any("CONSTANT_MEAN" in label for label in labels)


def test_selection_trace_figure_shows_inner_scores_and_gap() -> None:
    go, _pio, make_subplots = require_plotly()
    figure = build_selection_trace_figure(go, make_subplots, _tree_view())
    names = [str(trace.name) for trace in figure.data]
    assert "xgboost.regressor" in names
    assert "sklearn.ridge" in names
    assert "Train" in names
    assert "TEST" in names


def test_html_renders_tree_panels_when_sidecars_are_present(tmp_path: Path) -> None:
    output = tmp_path / "tree-report.html"
    render_predictive_research_report_html(_tree_view(), output)
    document = output.read_text(encoding="utf-8")
    assert 'id="feature_importance"' in document
    assert 'id="leaderboard"' in document
    assert 'id="selection_trace"' in document
    assert document.count("chart-block") >= 3
    assert "Native gain is a training-fold statistic" in document
    start = document.index('id="feature_importance"')
    end = document.find("<section", start + 1)
    assert "chart-block" in document[start:end]
    assert "Skipped" not in document[start:end]
