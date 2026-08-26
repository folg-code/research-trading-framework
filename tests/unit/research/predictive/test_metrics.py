"""Unmarked domain tests for Predictive Research metric formulae."""

from __future__ import annotations

import json
from types import MappingProxyType

import numpy as np
import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.metrics import (
    CALIBRATION_BIN_COUNT,
    CLASSIFICATION_DECISION_THRESHOLD,
    DECILE_COUNT,
    REGRESSION_DECISION_THRESHOLD,
    MetricSource,
    PredictiveMetricsReport,
    SourceMetrics,
    StatisticalMetrics,
    build_predictive_metrics_report,
    classification_statistical_metrics,
    default_decision_threshold,
    finance_metrics,
    fold_train_targets,
    permutation_shuffle,
    reference_baselines_for,
    regression_statistical_metrics,
)
from trading_framework.research.predictive.splitting import FoldRole


def test_regression_identity_scores() -> None:
    y = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    metrics = regression_statistical_metrics(y, y)
    assert metrics.rmse == pytest.approx(0.0)
    assert metrics.mae == pytest.approx(0.0)
    assert metrics.r_squared == pytest.approx(1.0)
    assert metrics.pearson_ic == pytest.approx(1.0)
    assert metrics.spearman_ic == pytest.approx(1.0)


def test_regression_known_rmse_mae_and_r_squared() -> None:
    y_true = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    y_pred = np.array([2.0, 2.0, 2.0], dtype=np.float64)
    metrics = regression_statistical_metrics(y_true, y_pred)
    assert metrics.rmse == pytest.approx(np.sqrt(2.0 / 3.0))
    assert metrics.mae == pytest.approx(2.0 / 3.0)
    assert metrics.r_squared == pytest.approx(1.0 - 2.0 / 2.0)


def test_spearman_is_pearson_of_ranks_and_ignores_monotonic_scale() -> None:
    y_true = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    y_pred = np.array([10.0, 20.0, 40.0, 80.0], dtype=np.float64)
    metrics = regression_statistical_metrics(y_true, y_pred)
    assert metrics.spearman_ic == pytest.approx(1.0)
    assert metrics.pearson_ic is not None
    assert metrics.pearson_ic < 1.0


def test_classification_perfect_scores() -> None:
    y_true = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    scores = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    metrics = classification_statistical_metrics(y_true, scores, threshold=0.5)
    assert metrics.accuracy == pytest.approx(1.0)
    assert metrics.balanced_accuracy == pytest.approx(1.0)
    assert metrics.roc_auc == pytest.approx(1.0)
    assert metrics.pr_auc == pytest.approx(1.0)
    assert metrics.brier_score == pytest.approx(0.025)
    assert metrics.log_loss is not None
    assert metrics.log_loss < 0.3


def test_classification_reversed_ranking_has_zero_roc_auc() -> None:
    y_true = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float64)
    scores = np.array([0.9, 0.8, 0.2, 0.1], dtype=np.float64)
    metrics = classification_statistical_metrics(y_true, scores, threshold=0.5)
    assert metrics.roc_auc == pytest.approx(0.0)
    assert metrics.accuracy == pytest.approx(0.0)


def test_balanced_accuracy_weights_classes_equally() -> None:
    y_true = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)
    scores = np.array([0.1, 0.2, 0.9, 0.8], dtype=np.float64)
    metrics = classification_statistical_metrics(y_true, scores, threshold=0.5)
    # TPR = 1, TNR = 2/3, balanced = 5/6. Accuracy would be 0.75.
    assert metrics.accuracy == pytest.approx(0.75)
    assert metrics.balanced_accuracy == pytest.approx(5.0 / 6.0)


def test_calibration_bins_are_ten_equal_width_probability_bins() -> None:
    y_true = np.array([0.0, 0.0, 1.0, 1.0, 1.0], dtype=np.float64)
    scores = np.array([0.05, 0.15, 0.55, 0.65, 1.0], dtype=np.float64)
    metrics = classification_statistical_metrics(y_true, scores, threshold=0.5)
    assert metrics.calibration_bins is not None
    bins = metrics.calibration_bins
    assert len(bins) == CALIBRATION_BIN_COUNT
    assert bins[0].lower == 0.0
    assert bins[0].upper == pytest.approx(0.1)
    assert bins[-1].lower == pytest.approx(0.9)
    assert bins[-1].upper == pytest.approx(1.0)
    assert bins[0].count == 1
    assert bins[0].mean_predicted == pytest.approx(0.05)
    assert bins[0].mean_observed == pytest.approx(0.0)
    assert bins[5].count == 1
    assert bins[9].count == 1
    assert bins[9].mean_observed == pytest.approx(1.0)
    empty = [bin_ for bin_ in bins if bin_.count == 0]
    assert empty
    assert all(bin_.mean_predicted is None and bin_.mean_observed is None for bin_ in empty)


def test_finance_metrics_use_forward_return_not_labels() -> None:
    scores = np.array([0.9, 0.8, 0.1, 0.2], dtype=np.float64)
    y_true = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float64)
    forward_return = np.array([-0.10, 0.20, 0.30, -0.05], dtype=np.float64)
    metrics = finance_metrics(scores, forward_return, threshold=0.5)
    # Selected = first two rows; hit rate from forward_return is 1/2, not from y_true (2/2).
    assert y_true[:2].mean() == pytest.approx(1.0)
    assert metrics.hit_rate == pytest.approx(0.5)
    assert metrics.coverage == pytest.approx(0.5)
    assert metrics.mean_forward_return_selected == pytest.approx(0.05)
    assert metrics.mean_forward_return_all == pytest.approx(0.0875)


def test_finance_deciles_and_top_bottom_spread() -> None:
    scores = np.arange(10, dtype=np.float64)
    forward_return = np.linspace(-0.09, 0.09, 10)
    metrics = finance_metrics(scores, forward_return, threshold=0.0)
    assert len(metrics.mean_forward_return_by_decile) == DECILE_COUNT
    assert metrics.mean_forward_return_by_decile[0] == pytest.approx(forward_return[0])
    assert metrics.mean_forward_return_by_decile[-1] == pytest.approx(forward_return[-1])
    assert metrics.top_bottom_spread == pytest.approx(forward_return[-1] - forward_return[0])
    assert metrics.coverage == pytest.approx(1.0)


def test_permutation_shuffle_is_deterministic_for_seed() -> None:
    values = np.arange(8, dtype=np.float64)
    first = permutation_shuffle(values, seed=7)
    second = permutation_shuffle(values, seed=7)
    other = permutation_shuffle(values, seed=8)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, values)
    assert not np.array_equal(first, other)
    assert sorted(first.tolist()) == values.tolist()


def test_report_includes_per_fold_pooled_and_task_baselines() -> None:
    predictions = _predictions_frame(
        fold_ids=[0, 0, 1, 1],
        y_true=[1.0, 3.0, 2.0, 4.0],
        y_pred=[1.5, 2.5, 1.0, 5.0],
        y_proba=[None, None, None, None],
        forward_return=[1.0, 3.0, 2.0, 4.0],
    )
    train_targets = {
        0: np.array([0.0, 2.0], dtype=np.float64),
        1: np.array([1.0, 3.0], dtype=np.float64),
    }
    report = build_predictive_metrics_report(
        predictions,
        train_targets_by_fold=train_targets,
        task_type=TaskType.REGRESSION,
        seed=7,
        run_id="0123456789abcdef",
    )
    assert set(report.folds) == {"0", "1"}
    assert MetricSource.MODEL.value in report.pooled
    assert MetricSource.CONSTANT_MEAN.value in report.pooled
    assert MetricSource.RANDOM_PERMUTATION.value in report.pooled
    assert MetricSource.MAJORITY_CLASS.value not in report.pooled
    for sources in report.folds.values():
        assert MetricSource.MODEL.value in sources
        assert MetricSource.CONSTANT_MEAN.value in sources
        assert MetricSource.RANDOM_PERMUTATION.value in sources
    constant = report.folds["0"][MetricSource.CONSTANT_MEAN.value]
    assert constant.statistical.mae == pytest.approx(1.0)
    payload = report.to_dict()
    assert "folds" in payload and "pooled" in payload
    round_trip = PredictiveMetricsReport.from_dict(payload)
    assert round_trip.folds.keys() == report.folds.keys()
    assert round_trip.pooled.keys() == report.pooled.keys()


def test_classification_report_uses_forward_return_and_majority_baseline() -> None:
    predictions = _predictions_frame(
        fold_ids=[0, 0, 0, 0],
        y_true=[1.0, 1.0, 0.0, 0.0],
        y_pred=[1.0, 1.0, 0.0, 0.0],
        y_proba=[0.9, 0.8, 0.1, 0.2],
        forward_return=[-0.10, 0.20, 0.30, -0.05],
    )
    train_targets = {0: np.array([0.0, 0.0, 1.0], dtype=np.float64)}
    report = build_predictive_metrics_report(
        predictions,
        train_targets_by_fold=train_targets,
        task_type=TaskType.CLASSIFICATION,
        seed=3,
        run_id="fedcba9876543210",
    )
    model_finance = report.pooled[MetricSource.MODEL.value].finance
    assert model_finance.hit_rate == pytest.approx(0.5)
    majority = report.pooled[MetricSource.MAJORITY_CLASS.value]
    assert majority.statistical.accuracy == pytest.approx(0.5)
    assert MetricSource.CONSTANT_MEAN.value not in report.pooled
    bins = report.pooled[MetricSource.MODEL.value].statistical.calibration_bins
    assert len(bins) == CALIBRATION_BIN_COUNT


def test_permutation_baseline_uses_estimator_seed() -> None:
    y_pred = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    predictions = _predictions_frame(
        fold_ids=[0] * len(y_pred),
        y_true=y_pred,
        y_pred=y_pred,
        y_proba=[None] * len(y_pred),
        forward_return=y_pred,
    )
    train_targets = {0: np.array([0.0, 1.0], dtype=np.float64)}
    report = build_predictive_metrics_report(
        predictions,
        train_targets_by_fold=train_targets,
        task_type=TaskType.REGRESSION,
        seed=7,
        run_id="aaaaaaaaaaaaaaaa",
    )
    expected = regression_statistical_metrics(
        np.asarray(y_pred, dtype=np.float64),
        permutation_shuffle(np.asarray(y_pred, dtype=np.float64), seed=7),
    )
    permuted = report.pooled[MetricSource.RANDOM_PERMUTATION.value].statistical
    assert permuted.spearman_ic == pytest.approx(expected.spearman_ic)
    assert permuted.mae == pytest.approx(expected.mae)
    assert permuted.mae != pytest.approx(0.0)
    other = build_predictive_metrics_report(
        predictions,
        train_targets_by_fold=train_targets,
        task_type=TaskType.REGRESSION,
        seed=99,
        run_id="aaaaaaaaaaaaaaaa",
    )
    other_expected = regression_statistical_metrics(
        np.asarray(y_pred, dtype=np.float64),
        permutation_shuffle(np.asarray(y_pred, dtype=np.float64), seed=99),
    )
    other_ic = other.pooled[MetricSource.RANDOM_PERMUTATION.value].statistical.spearman_ic
    assert other_ic == pytest.approx(other_expected.spearman_ic)


def test_reference_baselines_cover_constant_majority_and_permutation() -> None:
    assert reference_baselines_for(TaskType.REGRESSION) == (
        MetricSource.CONSTANT_MEAN,
        MetricSource.RANDOM_PERMUTATION,
    )
    assert reference_baselines_for(TaskType.CLASSIFICATION) == (
        MetricSource.MAJORITY_CLASS,
        MetricSource.RANDOM_PERMUTATION,
    )
    names = {
        *reference_baselines_for(TaskType.REGRESSION),
        *reference_baselines_for(TaskType.CLASSIFICATION),
    }
    assert names == {
        MetricSource.CONSTANT_MEAN,
        MetricSource.MAJORITY_CLASS,
        MetricSource.RANDOM_PERMUTATION,
    }


def test_default_thresholds_match_wave0() -> None:
    assert default_decision_threshold(TaskType.CLASSIFICATION) == CLASSIFICATION_DECISION_THRESHOLD
    assert default_decision_threshold(TaskType.REGRESSION) == REGRESSION_DECISION_THRESHOLD
    assert CLASSIFICATION_DECISION_THRESHOLD == 0.5
    assert REGRESSION_DECISION_THRESHOLD == 0.0


def test_pooled_only_report_is_rejected() -> None:
    empty_source = SourceMetrics(
        statistical=StatisticalMetrics(rmse=0.0, mae=0.0, r_squared=1.0),
        finance=finance_metrics(
            np.array([0.1, 0.2], dtype=np.float64),
            np.array([0.1, 0.2], dtype=np.float64),
            threshold=0.0,
        ),
    )
    with pytest.raises(ValidationError, match="per-fold"):
        PredictiveMetricsReport(
            schema_version="predictive_metrics.v1",
            run_id="0123456789abcdef",
            task_type=TaskType.REGRESSION,
            decision_threshold=0.0,
            seed=1,
            folds=MappingProxyType({}),
            pooled={
                MetricSource.MODEL.value: empty_source,
                MetricSource.CONSTANT_MEAN.value: empty_source,
                MetricSource.RANDOM_PERMUTATION.value: empty_source,
            },
        )


def test_fold_train_targets_reads_train_labels_only() -> None:
    features = pl.DataFrame(
        {
            "fold_id": [0, 0, 0, 1],
            "fold_role": [
                FoldRole.TRAIN.value,
                FoldRole.TEST.value,
                FoldRole.PURGED.value,
                FoldRole.TRAIN.value,
            ],
            "label": [1.5, 9.0, 8.0, 2.5],
        }
    )
    targets = fold_train_targets(features)
    assert targets[0].tolist() == [1.5]
    assert targets[1].tolist() == [2.5]


def test_metrics_json_round_trip_is_finite() -> None:
    predictions = _predictions_frame(
        fold_ids=[0, 0],
        y_true=[0.0, 1.0],
        y_pred=[0.2, 0.8],
        y_proba=[0.2, 0.8],
        forward_return=[-0.01, 0.04],
    )
    report = build_predictive_metrics_report(
        predictions,
        train_targets_by_fold={0: np.array([0.0, 1.0, 1.0], dtype=np.float64)},
        task_type=TaskType.CLASSIFICATION,
        seed=2,
        run_id="bbbbbbbbbbbbbbbb",
    )
    encoded = json.dumps(report.to_dict())
    parsed = json.loads(encoded)
    assert parsed["folds"]["0"]["MODEL"]["finance"]["hit_rate"] == pytest.approx(1.0)


def _predictions_frame(
    *,
    fold_ids: list[int],
    y_true: list[float],
    y_pred: list[float],
    y_proba: list[float | None],
    forward_return: list[float],
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "entity_id": [str(index) for index in range(len(fold_ids))],
            "fold_id": fold_ids,
            "y_true": y_true,
            "y_pred": y_pred,
            "y_proba": y_proba,
            "forward_return": forward_return,
        },
        schema={
            "entity_id": pl.String(),
            "fold_id": pl.Int64(),
            "y_true": pl.Float64(),
            "y_pred": pl.Float64(),
            "y_proba": pl.Float64(),
            "forward_return": pl.Float64(),
        },
    )
