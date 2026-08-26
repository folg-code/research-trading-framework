"""Display series derived from persisted predictions and metrics.

Visualization only — never model output. Numpy and polars; no sklearn.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import polars as pl

from trading_framework.research.predictive.metrics import (
    CALIBRATION_BIN_COUNT,
    DECILE_COUNT,
    CalibrationBin,
)

MAX_SCATTER_POINTS = 2000
RESIDUAL_BIN_COUNT = 20


@dataclass(frozen=True, slots=True)
class ScatterSeries:
    predicted: np.ndarray
    realized: np.ndarray
    slope: float | None
    intercept: float | None


@dataclass(frozen=True, slots=True)
class ResidualHistogram:
    centers: np.ndarray
    counts: np.ndarray


@dataclass(frozen=True, slots=True)
class CurveSeries:
    fold_id: int | None
    x: np.ndarray
    y: np.ndarray


@dataclass(frozen=True, slots=True)
class ReliabilityPoint:
    mean_predicted: float
    mean_observed: float
    count: int


@dataclass(frozen=True, slots=True)
class BrierDecomposition:
    reliability: float
    resolution: float
    uncertainty: float
    persisted_brier: float | None


@dataclass(frozen=True, slots=True)
class DecileBucket:
    decile: int
    mean_forward_return: float | None
    count: int


def prediction_scores(predictions: pl.DataFrame) -> np.ndarray:
    """Prefer persisted probabilities; otherwise use hard predictions."""
    if "y_proba" in predictions.columns:
        values = predictions.get_column("y_proba").to_list()
        if any(value is not None and value == value for value in values):
            return np.asarray(
                [np.nan if value is None else float(value) for value in values],
                dtype=np.float64,
            )
    return _float_column(predictions, "y_pred")


def build_scatter_series(predictions: pl.DataFrame) -> ScatterSeries:
    predicted = _float_column(predictions, "y_pred")
    realized = _float_column(predictions, "y_true")
    slope, intercept = _fitted_line(predicted, realized)
    return ScatterSeries(
        predicted=downsample(predicted),
        realized=downsample(realized),
        slope=slope,
        intercept=intercept,
    )


def build_residual_histogram(predictions: pl.DataFrame) -> ResidualHistogram:
    residuals = _float_column(predictions, "y_true") - _float_column(predictions, "y_pred")
    if residuals.size == 0:
        return ResidualHistogram(centers=np.array([]), counts=np.array([]))
    counts, edges = np.histogram(residuals, bins=RESIDUAL_BIN_COUNT)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return ResidualHistogram(centers=centers, counts=counts.astype(np.int64))


def build_roc_curves(predictions: pl.DataFrame) -> tuple[CurveSeries, ...]:
    return _grouped_curves(predictions, _roc_points)


def build_pr_curves(predictions: pl.DataFrame) -> tuple[CurveSeries, ...]:
    return _grouped_curves(predictions, _pr_points)


def reliability_points(bins: tuple[CalibrationBin, ...]) -> tuple[ReliabilityPoint, ...]:
    points: list[ReliabilityPoint] = []
    for bin_ in bins:
        if bin_.count <= 0 or bin_.mean_predicted is None or bin_.mean_observed is None:
            continue
        points.append(
            ReliabilityPoint(
                mean_predicted=bin_.mean_predicted,
                mean_observed=bin_.mean_observed,
                count=bin_.count,
            )
        )
    return tuple(points)


def brier_decomposition(
    bins: tuple[CalibrationBin, ...],
    *,
    persisted_brier: float | None,
) -> BrierDecomposition | None:
    occupied = reliability_points(bins)
    total = sum(point.count for point in occupied)
    if total == 0:
        return None
    observed_bar = sum(point.count * point.mean_observed for point in occupied) / total
    reliability = (
        sum(point.count * (point.mean_predicted - point.mean_observed) ** 2 for point in occupied)
        / total
    )
    resolution = (
        sum(point.count * (point.mean_observed - observed_bar) ** 2 for point in occupied) / total
    )
    uncertainty = observed_bar * (1.0 - observed_bar)
    return BrierDecomposition(
        reliability=reliability,
        resolution=resolution,
        uncertainty=uncertainty,
        persisted_brier=persisted_brier,
    )


def build_prediction_buckets(predictions: pl.DataFrame) -> tuple[DecileBucket, ...]:
    scores = prediction_scores(predictions)
    returns = _float_column(predictions, "forward_return")
    mask = np.isfinite(scores) & np.isfinite(returns)
    scores = scores[mask]
    returns = returns[mask]
    n = scores.shape[0]
    if n == 0:
        return tuple(
            DecileBucket(decile=index, mean_forward_return=None, count=0)
            for index in range(1, DECILE_COUNT + 1)
        )
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(n, dtype=np.int64)
    ranks[order] = np.arange(n)
    decile_ids = np.minimum(DECILE_COUNT, ranks * DECILE_COUNT // n + 1)
    filled: list[DecileBucket] = []
    for decile in range(1, DECILE_COUNT + 1):
        selected = returns[decile_ids == decile]
        count = int(selected.size)
        mean = float(np.mean(selected)) if count else None
        filled.append(DecileBucket(decile=decile, mean_forward_return=mean, count=count))
    return tuple(filled)


def calibration_bins_from_predictions(predictions: pl.DataFrame) -> tuple[CalibrationBin, ...]:
    scores = prediction_scores(predictions)
    labels = _float_column(predictions, "y_true")
    mask = np.isfinite(scores) & np.isfinite(labels)
    scores = np.clip(scores[mask], 0.0, 1.0)
    positive = labels[mask] > 0.5
    if scores.size == 0:
        return ()
    bin_index = np.minimum(
        (scores * CALIBRATION_BIN_COUNT).astype(np.int64), CALIBRATION_BIN_COUNT - 1
    )
    bins: list[CalibrationBin] = []
    for index in range(CALIBRATION_BIN_COUNT):
        lower = index / CALIBRATION_BIN_COUNT
        upper = (index + 1) / CALIBRATION_BIN_COUNT
        selected = bin_index == index
        count = int(selected.sum())
        if count == 0:
            bins.append(
                CalibrationBin(
                    bin_index=index,
                    lower=lower,
                    upper=upper,
                    count=0,
                    mean_predicted=None,
                    mean_observed=None,
                )
            )
            continue
        bins.append(
            CalibrationBin(
                bin_index=index,
                lower=lower,
                upper=upper,
                count=count,
                mean_predicted=float(np.mean(scores[selected])),
                mean_observed=float(np.mean(positive[selected].astype(np.float64))),
            )
        )
    return tuple(bins)


def downsample(values: np.ndarray, *, max_points: int = MAX_SCATTER_POINTS) -> np.ndarray:
    if values.shape[0] <= max_points:
        return values
    stride = int(np.ceil(values.shape[0] / max_points))
    return values[::stride]


def _float_column(frame: pl.DataFrame, name: str) -> np.ndarray:
    return np.asarray(
        [np.nan if value is None else float(value) for value in frame.get_column(name).to_list()],
        dtype=np.float64,
    )


def _fitted_line(predicted: np.ndarray, realized: np.ndarray) -> tuple[float | None, float | None]:
    mask = np.isfinite(predicted) & np.isfinite(realized)
    if int(mask.sum()) < 2:
        return None, None
    x = predicted[mask]
    y = realized[mask]
    if np.unique(x).size < 2:
        return None, None
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def _grouped_curves(
    predictions: pl.DataFrame,
    builder: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]],
) -> tuple[CurveSeries, ...]:
    scores = prediction_scores(predictions)
    labels = _float_column(predictions, "y_true")
    fold_ids = np.asarray(predictions.get_column("fold_id").to_list(), dtype=np.int64)
    series: list[CurveSeries] = []
    for fold_id in sorted(set(fold_ids.tolist())):
        mask = fold_ids == fold_id
        x, y = builder(labels[mask], scores[mask])
        series.append(CurveSeries(fold_id=int(fold_id), x=x, y=y))
    x, y = builder(labels, scores)
    series.append(CurveSeries(fold_id=None, x=x, y=y))
    return tuple(series)


def _roc_points(labels: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(labels) & np.isfinite(scores)
    positive = (labels[mask] > 0.5).astype(np.float64)
    ranked = scores[mask]
    n_pos = float(positive.sum())
    n_neg = float(positive.size - n_pos)
    if n_pos == 0.0 or n_neg == 0.0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])
    order = np.argsort(-ranked, kind="mergesort")
    sorted_positive = positive[order]
    tps = np.cumsum(sorted_positive)
    fps = np.cumsum(1.0 - sorted_positive)
    fpr = np.concatenate(([0.0], fps / n_neg, [1.0]))
    tpr = np.concatenate(([0.0], tps / n_pos, [1.0]))
    return fpr, tpr


def _pr_points(labels: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(labels) & np.isfinite(scores)
    positive = (labels[mask] > 0.5).astype(np.float64)
    ranked = scores[mask]
    n_pos = float(positive.sum())
    if n_pos == 0.0 or positive.size == 0:
        return np.array([0.0, 1.0]), np.array([1.0, 0.0])
    order = np.argsort(-ranked, kind="mergesort")
    sorted_positive = positive[order]
    tps = np.cumsum(sorted_positive)
    fps = np.cumsum(1.0 - sorted_positive)
    recall = np.concatenate(([0.0], tps / n_pos))
    precision = np.concatenate(([1.0], tps / np.maximum(tps + fps, 1.0)))
    return recall, precision
