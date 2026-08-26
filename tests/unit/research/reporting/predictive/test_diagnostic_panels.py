"""Tests for Predictive Research diagnostic Plotly panels."""

from __future__ import annotations

from trading_framework.research.reporting.predictive.plotly_figures import (
    build_fold_timeline_figure,
    build_metric_stability_figure,
    build_model_vs_baselines_figure,
    build_sample_composition_figure,
    require_plotly,
)
from trading_framework.research.reporting.predictive.view_models import (
    build_predictive_report_view_model,
)
from trading_framework.time.clocks.fixed import FixedClock

from tests.unit.research.reporting.predictive.test_view_model import (
    _GENERATED,
    _source_report,
)

_TIMELINE_ROLE_ORDER = ("TRAIN", "PURGED", "EMBARGOED", "TEST")


def _view():
    return build_predictive_report_view_model(
        _source_report(),
        clock=FixedClock(_GENERATED),
    )


def test_fold_timeline_has_all_four_roles_with_counts() -> None:
    go, _pio, _subplots = require_plotly()
    view = _view()
    figure = build_fold_timeline_figure(go, view)
    names = [str(trace.name) for trace in figure.data]
    assert names == list(_TIMELINE_ROLE_ORDER)
    for trace, role in zip(figure.data, _TIMELINE_ROLE_ORDER, strict=True):
        bands = [band for band in view.fold_timeline if band.role == role]
        assert list(trace.text) == [f"{band.row_count:,}" for band in bands]
        assert len(trace.y) == len(bands)
        assert all(count > 0 for count in (band.row_count for band in bands))


def test_metric_stability_plots_per_fold_points_and_pooled_line() -> None:
    go, _pio, _subplots = require_plotly()
    view = _view()
    figure = build_metric_stability_figure(go, view)
    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [snapshot.model for snapshot in view.fold_metrics]
    shapes = figure.layout.shapes or ()
    pooled_lines = [shape for shape in shapes if shape.y0 == shape.y1]
    assert len(pooled_lines) == 1
    assert pooled_lines[0].y0 == view.pooled_model
    spread_bands = [shape for shape in shapes if shape.y0 != shape.y1]
    assert len(spread_bands) == 1
    fold_values = [snapshot.model for snapshot in view.fold_metrics if snapshot.model is not None]
    assert spread_bands[0].y0 == min(fold_values)
    assert spread_bands[0].y1 == max(fold_values)


def test_model_vs_baselines_includes_model_and_references() -> None:
    go, _pio, _subplots = require_plotly()
    view = _view()
    figure = build_model_vs_baselines_figure(go, view)
    names = {str(trace.name) for trace in figure.data}
    assert "MODEL" in names
    assert "RANDOM_PERMUTATION" in names
    assert "CONSTANT_MEAN" in names
    pooled_index = list(figure.data[0].x).index("Pooled")
    assert figure.data[0].y[pooled_index] == view.pooled_model
    for snapshot_index, snapshot in enumerate(view.fold_metrics):
        assert figure.data[0].y[snapshot_index] == snapshot.model


def test_sample_composition_shows_exclusions_and_roles() -> None:
    go, _pio, make_subplots = require_plotly()
    view = _view()
    figure = build_sample_composition_figure(go, make_subplots, view)
    assert len(figure.data) == 2
    exclusion_trace, role_trace = figure.data
    assert list(exclusion_trace.x) == list(view.exclusion_counts)
    assert list(role_trace.x) == list(_TIMELINE_ROLE_ORDER)
    assert list(role_trace.y) == [
        int(view.role_counts.get(role, 0)) for role in _TIMELINE_ROLE_ORDER
    ]
