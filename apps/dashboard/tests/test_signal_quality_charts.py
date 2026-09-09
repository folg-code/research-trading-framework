"""Tests for the BTC Signal Quality study's three chart builders (Sprint 060 T003)."""

from __future__ import annotations

from dashboard_app.charts import (
    build_signal_quality_fold_roc_auc_figure,
    build_signal_quality_threshold_coverage_figure,
    build_signal_quality_trade_disposition_figure,
)
from dashboard_app.contracts import (
    SignalQualityFoldRocAucRow,
    SignalQualityThresholdPoint,
    SignalQualityTradeDispositionRow,
)


def test_fold_roc_auc_figure_includes_pooled_and_folds() -> None:
    pooled = SignalQualityFoldRocAucRow("Pooled", 0.5239, 0.5070)
    folds = (
        SignalQualityFoldRocAucRow("Fold 0", 0.5343, 0.4880),
        SignalQualityFoldRocAucRow("Fold 1", 0.5100, 0.5155),
    )

    figure = build_signal_quality_fold_roc_auc_figure(pooled, folds)

    assert len(figure.data) == 2
    model_trace, permutation_trace = figure.data
    assert list(model_trace.x) == ["Pooled", "Fold 0", "Fold 1"]
    assert list(model_trace.y) == [0.5239, 0.5343, 0.5100]
    assert list(permutation_trace.y) == [0.5070, 0.4880, 0.5155]


def test_fold_roc_auc_figure_degrades_to_empty_on_no_data() -> None:
    figure = build_signal_quality_fold_roc_auc_figure(None, ())

    assert len(figure.data) == 0


def test_threshold_coverage_figure_shows_coverage_and_hit_rate_sorted() -> None:
    points = (
        SignalQualityThresholdPoint(0.6, 0.013, 0.644),
        SignalQualityThresholdPoint(0.05, 1.0, 0.551),
    )

    figure = build_signal_quality_threshold_coverage_figure(points)

    assert len(figure.data) == 2
    coverage_trace, hit_rate_trace = figure.data
    assert list(coverage_trace.x) == [0.05, 0.6]
    assert list(coverage_trace.y) == [1.0, 0.013]
    assert list(hit_rate_trace.y) == [0.551, 0.644]


def test_threshold_coverage_figure_degrades_to_empty_on_no_data() -> None:
    figure = build_signal_quality_threshold_coverage_figure(())

    assert len(figure.data) == 0


def test_trade_disposition_figure_shows_baseline_and_scored() -> None:
    rows = (
        SignalQualityTradeDispositionRow("Baseline", 6200, 0.5135, 1198499.9),
        SignalQualityTradeDispositionRow("Scored", 6198, 0.5136, 1206906.6),
    )

    figure = build_signal_quality_trade_disposition_figure(rows)

    assert len(figure.data) == 3  # trade_count, win_rate, net_pnl subplots
    trade_count_trace = figure.data[0]
    assert list(trade_count_trace.x) == ["Baseline", "Scored"]
    assert list(trade_count_trace.y) == [6200, 6198]


def test_trade_disposition_figure_degrades_to_empty_on_no_data() -> None:
    figure = build_signal_quality_trade_disposition_figure(())

    assert len(figure.data) == 0
