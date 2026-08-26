"""Tests for Predictive Research task-specific report panels."""

from __future__ import annotations

import numpy as np
import pytest

from tests.unit.research.reporting.predictive.test_view_model import (
    _GENERATED,
    _source_report,
)
from trading_framework.research.predictive.metrics import DECILE_COUNT
from trading_framework.research.reporting.predictive.display_series import (
    MAX_SCATTER_POINTS,
    build_prediction_buckets,
    build_residual_histogram,
    build_roc_curves,
    build_scatter_series,
    downsample,
)
from trading_framework.research.reporting.predictive.plotly_figures import (
    build_calibration_figure,
    build_discrimination_figure,
    build_prediction_buckets_figure,
    build_prediction_quality_figure,
    require_plotly,
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


def test_scatter_series_fits_identity_on_known_predictions() -> None:
    view = _view()
    scatter = build_scatter_series(view.predictions)
    assert scatter.slope == pytest.approx(1.0)
    np.testing.assert_allclose(scatter.predicted, scatter.realized)
    residuals = build_residual_histogram(view.predictions)
    assert int(residuals.counts.sum()) == view.predictions.height


def test_downsample_is_deterministic_and_keeps_pairs_aligned() -> None:
    values = np.arange(MAX_SCATTER_POINTS * 3, dtype=np.float64)
    first = downsample(values)
    second = downsample(values)
    np.testing.assert_array_equal(first, second)
    assert first.shape[0] <= MAX_SCATTER_POINTS
    assert first[0] == 0.0


def test_prediction_quality_figure_has_scatter_ic_and_residuals() -> None:
    go, _pio, make_subplots = require_plotly()
    view = _view()
    figure = build_prediction_quality_figure(go, make_subplots, view)
    names = [str(trace.name) for trace in figure.data]
    assert "OOS rows" in names
    assert "Rank IC" in names
    assert "Residuals" in names
    ic_trace = next(trace for trace in figure.data if trace.name == "Rank IC")
    assert list(ic_trace.y) == [snapshot.model for snapshot in view.fold_metrics]


def test_roc_curves_include_per_fold_and_pooled() -> None:
    view = _view(binary=True, with_proba=True)
    series = build_roc_curves(view.predictions)
    fold_ids = {curve.fold_id for curve in series}
    assert None in fold_ids
    assert fold_ids - {None} == {snapshot.fold_id for snapshot in view.fold_metrics}
    pooled = next(curve for curve in series if curve.fold_id is None)
    assert pooled.x[0] == 0.0
    assert pooled.x[-1] == 1.0


def test_discrimination_figure_emphasizes_pooled_curve() -> None:
    go, _pio, make_subplots = require_plotly()
    view = _view(binary=True, with_proba=True)
    figure = build_discrimination_figure(go, make_subplots, view)
    pooled = [trace for trace in figure.data if trace.name == "Pooled"]
    assert len(pooled) == 2
    assert all(trace.line.width == 3 for trace in pooled)


def test_calibration_figure_plots_occupied_bins_and_brier_parts() -> None:
    go, _pio, make_subplots = require_plotly()
    view = _view(binary=True, with_proba=True)
    figure = build_calibration_figure(go, make_subplots, view)
    names = [str(trace.name) for trace in figure.data]
    assert "Occupied bins" in names
    brier_trace = figure.data[-1]
    assert list(brier_trace.x) == ["Reliability", "Resolution", "Uncertainty"]


def test_prediction_buckets_cover_all_oos_rows() -> None:
    view = _view()
    buckets = build_prediction_buckets(view.predictions)
    assert len(buckets) == DECILE_COUNT
    assert sum(bucket.count for bucket in buckets) == view.predictions.height
    means = [
        bucket.mean_forward_return for bucket in buckets if bucket.mean_forward_return is not None
    ]
    assert means == sorted(means)


def test_prediction_buckets_figure_has_all_rows_reference() -> None:
    go, _pio, _subplots = require_plotly()
    view = _view()
    figure = build_prediction_buckets_figure(go, view)
    assert len(figure.data) == 1
    assert figure.data[0].y[0] is not None
    shapes = list(figure.layout.shapes or ())
    assert len(shapes) == 1
    assert shapes[0].y0 == view.mean_forward_return_all
