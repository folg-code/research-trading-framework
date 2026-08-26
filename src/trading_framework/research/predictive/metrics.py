"""Statistical and finance-aware metrics for Predictive Research (D-S040-20, D-S040-21).

Library-free: numpy and polars only. Do not import sklearn.metrics.

Reference baselines are metric-layer comparisons, not estimator-registry families.
Finance-aware metrics always use the carried ``forward_return`` column, never
recomputed outcomes. Classification must not substitute ``y_true`` (0/1) for
forward return.

Every report includes per-fold and pooled results. Pooled-only output is invalid.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.splitting import FoldRole

PREDICTIVE_METRICS_SCHEMA_VERSION = "predictive_metrics.v1"
CALIBRATION_BIN_COUNT = 10
DECILE_COUNT = 10
CLASSIFICATION_DECISION_THRESHOLD = 0.5
REGRESSION_DECISION_THRESHOLD = 0.0
_LOG_LOSS_EPS = 1e-15
_REQUIRED_PREDICTION_COLUMNS = (
    "fold_id",
    "y_true",
    "y_pred",
    "y_proba",
    "forward_return",
)


class MetricSource(StrEnum):
    """Who produced the scored predictions being measured."""

    MODEL = "MODEL"
    CONSTANT_MEAN = "CONSTANT_MEAN"
    MAJORITY_CLASS = "MAJORITY_CLASS"
    RANDOM_PERMUTATION = "RANDOM_PERMUTATION"


def default_decision_threshold(task_type: TaskType) -> float:
    """Return the D-S040-21 default decision threshold for a task type."""
    if task_type is TaskType.CLASSIFICATION:
        return CLASSIFICATION_DECISION_THRESHOLD
    return REGRESSION_DECISION_THRESHOLD


def reference_baselines_for(task_type: TaskType) -> tuple[MetricSource, ...]:
    """Return the metric-layer baselines that apply to ``task_type``."""
    if task_type is TaskType.REGRESSION:
        return (MetricSource.CONSTANT_MEAN, MetricSource.RANDOM_PERMUTATION)
    return (MetricSource.MAJORITY_CLASS, MetricSource.RANDOM_PERMUTATION)


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    """One equal-width predicted-probability bin on ``[0, 1]``."""

    bin_index: int
    lower: float
    upper: float
    count: int
    mean_predicted: float | None
    mean_observed: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bin_index": self.bin_index,
            "lower": self.lower,
            "upper": self.upper,
            "count": self.count,
            "mean_predicted": self.mean_predicted,
            "mean_observed": self.mean_observed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CalibrationBin:
        return cls(
            bin_index=int(payload["bin_index"]),
            lower=float(payload["lower"]),
            upper=float(payload["upper"]),
            count=int(payload["count"]),
            mean_predicted=_optional_float(payload.get("mean_predicted")),
            mean_observed=_optional_float(payload.get("mean_observed")),
        )


@dataclass(frozen=True, slots=True)
class StatisticalMetrics:
    """Task-typed statistical scores. Unused fields are ``None``."""

    rmse: float | None = None
    mae: float | None = None
    r_squared: float | None = None
    spearman_ic: float | None = None
    pearson_ic: float | None = None
    accuracy: float | None = None
    balanced_accuracy: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    log_loss: float | None = None
    brier_score: float | None = None
    calibration_bins: tuple[CalibrationBin, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "rmse": self.rmse,
            "mae": self.mae,
            "r_squared": self.r_squared,
            "spearman_ic": self.spearman_ic,
            "pearson_ic": self.pearson_ic,
            "accuracy": self.accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "roc_auc": self.roc_auc,
            "pr_auc": self.pr_auc,
            "log_loss": self.log_loss,
            "brier_score": self.brier_score,
        }
        if self.calibration_bins:
            payload["calibration_bins"] = [bin_.to_dict() for bin_ in self.calibration_bins]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StatisticalMetrics:
        bins_raw = payload.get("calibration_bins", ())
        bins = tuple(CalibrationBin.from_dict(item) for item in bins_raw) if bins_raw else ()
        return cls(
            rmse=_optional_float(payload.get("rmse")),
            mae=_optional_float(payload.get("mae")),
            r_squared=_optional_float(payload.get("r_squared")),
            spearman_ic=_optional_float(payload.get("spearman_ic")),
            pearson_ic=_optional_float(payload.get("pearson_ic")),
            accuracy=_optional_float(payload.get("accuracy")),
            balanced_accuracy=_optional_float(payload.get("balanced_accuracy")),
            roc_auc=_optional_float(payload.get("roc_auc")),
            pr_auc=_optional_float(payload.get("pr_auc")),
            log_loss=_optional_float(payload.get("log_loss")),
            brier_score=_optional_float(payload.get("brier_score")),
            calibration_bins=bins,
        )


@dataclass(frozen=True, slots=True)
class FinanceMetrics:
    """Finance-aware scores over TEST/OOS rows using carried ``forward_return``."""

    mean_forward_return_by_decile: tuple[float | None, ...]
    top_bottom_spread: float | None
    hit_rate: float | None
    coverage: float
    mean_forward_return_selected: float | None
    mean_forward_return_all: float | None

    def __post_init__(self) -> None:
        if len(self.mean_forward_return_by_decile) != DECILE_COUNT:
            msg = f"mean_forward_return_by_decile must have {DECILE_COUNT} entries"
            raise ValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean_forward_return_by_decile": list(self.mean_forward_return_by_decile),
            "top_bottom_spread": self.top_bottom_spread,
            "hit_rate": self.hit_rate,
            "coverage": self.coverage,
            "mean_forward_return_selected": self.mean_forward_return_selected,
            "mean_forward_return_all": self.mean_forward_return_all,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FinanceMetrics:
        deciles_raw = payload["mean_forward_return_by_decile"]
        if not isinstance(deciles_raw, list):
            msg = "mean_forward_return_by_decile must be a list"
            raise ValidationError(msg)
        return cls(
            mean_forward_return_by_decile=tuple(_optional_float(value) for value in deciles_raw),
            top_bottom_spread=_optional_float(payload.get("top_bottom_spread")),
            hit_rate=_optional_float(payload.get("hit_rate")),
            coverage=float(payload["coverage"]),
            mean_forward_return_selected=_optional_float(
                payload.get("mean_forward_return_selected")
            ),
            mean_forward_return_all=_optional_float(payload.get("mean_forward_return_all")),
        )


@dataclass(frozen=True, slots=True)
class SourceMetrics:
    """Statistical plus finance-aware metrics for one prediction source."""

    statistical: StatisticalMetrics
    finance: FinanceMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "statistical": self.statistical.to_dict(),
            "finance": self.finance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SourceMetrics:
        statistical = payload.get("statistical", {})
        finance = payload.get("finance", {})
        if not isinstance(statistical, Mapping) or not isinstance(finance, Mapping):
            msg = "source metrics must include statistical and finance mappings"
            raise ValidationError(msg)
        return cls(
            statistical=StatisticalMetrics.from_dict(statistical),
            finance=FinanceMetrics.from_dict(finance),
        )


@dataclass(frozen=True, slots=True)
class PredictiveMetricsReport:
    """Per-fold and pooled metrics, including reference baselines.

    ``folds`` must be non-empty. Pooled-only reports are rejected.
    """

    schema_version: str
    run_id: str
    task_type: TaskType
    decision_threshold: float
    seed: int
    folds: Mapping[str, Mapping[str, SourceMetrics]]
    pooled: Mapping[str, SourceMetrics]

    def __post_init__(self) -> None:
        object.__setattr__(self, "folds", _freeze_fold_metrics(self.folds))
        object.__setattr__(self, "pooled", _freeze_source_metrics(self.pooled))
        if not self.folds:
            msg = "metrics must include per-fold results; pooled-only output is invalid"
            raise ValidationError(msg)
        if not self.pooled:
            msg = "metrics must include pooled results"
            raise ValidationError(msg)
        required = {
            MetricSource.MODEL.value,
            *(item.value for item in reference_baselines_for(self.task_type)),
        }
        for fold_id, sources in self.folds.items():
            missing = required.difference(sources)
            if missing:
                msg = f"fold {fold_id} missing metric sources: {sorted(missing)}"
                raise ValidationError(msg)
        missing_pooled = required.difference(self.pooled)
        if missing_pooled:
            msg = f"pooled metrics missing sources: {sorted(missing_pooled)}"
            raise ValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "task_type": self.task_type.value,
            "decision_threshold": self.decision_threshold,
            "seed": self.seed,
            "folds": {
                fold_id: {source: metrics.to_dict() for source, metrics in sources.items()}
                for fold_id, sources in self.folds.items()
            },
            "pooled": {source: metrics.to_dict() for source, metrics in self.pooled.items()},
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PredictiveMetricsReport:
        folds_raw = payload.get("folds", {})
        pooled_raw = payload.get("pooled", {})
        if not isinstance(folds_raw, Mapping) or not isinstance(pooled_raw, Mapping):
            msg = "metrics payload must include folds and pooled mappings"
            raise ValidationError(msg)
        try:
            task_type = TaskType(str(payload["task_type"]))
        except (KeyError, ValueError) as exc:
            msg = f"invalid metrics task_type: {payload.get('task_type')!r}"
            raise ValidationError(msg) from exc
        return cls(
            schema_version=str(payload["schema_version"]),
            run_id=str(payload["run_id"]),
            task_type=task_type,
            decision_threshold=float(payload["decision_threshold"]),
            seed=int(payload["seed"]),
            folds={
                str(fold_id): {
                    str(source): SourceMetrics.from_dict(metrics)
                    for source, metrics in sources.items()
                }
                for fold_id, sources in folds_raw.items()
            },
            pooled={
                str(source): SourceMetrics.from_dict(metrics)
                for source, metrics in pooled_raw.items()
            },
        )


def fold_train_targets(features: pl.DataFrame) -> dict[int, np.ndarray]:
    """Extract TRAIN-fold label vectors from a labelled matrix with fold roles."""
    missing = [name for name in ("fold_id", "fold_role", "label") if name not in features.columns]
    if missing:
        msg = f"labelled matrix missing required column: {missing[0]}"
        raise ValidationError(msg)
    targets: dict[int, np.ndarray] = {}
    fold_ids = sorted({int(value) for value in features.get_column("fold_id").to_list()})
    for fold_id in fold_ids:
        train = features.filter(
            (pl.col("fold_id") == fold_id) & (pl.col("fold_role") == FoldRole.TRAIN.value)
        )
        if train.height == 0:
            msg = f"fold {fold_id} has no TRAIN rows"
            raise ValidationError(msg)
        targets[fold_id] = np.asarray(train.get_column("label").to_list(), dtype=np.float64)
    return targets


def build_predictive_metrics_report(
    predictions: pl.DataFrame,
    *,
    train_targets_by_fold: Mapping[int, np.ndarray],
    task_type: TaskType,
    seed: int,
    run_id: str,
    decision_threshold: float | None = None,
) -> PredictiveMetricsReport:
    """Compute per-fold and pooled model plus reference-baseline metrics."""
    _require_prediction_columns(predictions)
    if predictions.height == 0:
        msg = "predictions must contain at least one TEST row"
        raise ValidationError(msg)
    threshold = (
        default_decision_threshold(task_type)
        if decision_threshold is None
        else float(decision_threshold)
    )
    fold_ids = np.asarray(predictions.get_column("fold_id").to_list(), dtype=np.int64)
    y_true = _float_column(predictions, "y_true")
    y_pred = _float_column(predictions, "y_pred")
    y_proba = _float_column(predictions, "y_proba")
    forward_return = _float_column(predictions, "forward_return")
    scores = _decision_scores(task_type, y_pred=y_pred, y_proba=y_proba)

    unique_folds = tuple(int(value) for value in sorted(set(fold_ids.tolist())))
    if not unique_folds:
        msg = "predictions must include fold_id values"
        raise ValidationError(msg)
    for fold_id in unique_folds:
        if fold_id not in train_targets_by_fold:
            msg = f"missing TRAIN targets for fold {fold_id}"
            raise ValidationError(msg)

    fold_payload: dict[str, dict[str, SourceMetrics]] = {}
    for fold_id in unique_folds:
        mask = fold_ids == fold_id
        fold_payload[str(fold_id)] = _metrics_for_sources(
            y_true=y_true[mask],
            y_pred=y_pred[mask],
            scores=scores[mask],
            forward_return=forward_return[mask],
            fold_ids=fold_ids[mask],
            train_targets_by_fold=train_targets_by_fold,
            task_type=task_type,
            seed=seed,
            threshold=threshold,
        )
    pooled = _metrics_for_sources(
        y_true=y_true,
        y_pred=y_pred,
        scores=scores,
        forward_return=forward_return,
        fold_ids=fold_ids,
        train_targets_by_fold=train_targets_by_fold,
        task_type=task_type,
        seed=seed,
        threshold=threshold,
    )
    return PredictiveMetricsReport(
        schema_version=PREDICTIVE_METRICS_SCHEMA_VERSION,
        run_id=run_id,
        task_type=task_type,
        decision_threshold=threshold,
        seed=seed,
        folds=fold_payload,
        pooled=pooled,
    )


def permutation_shuffle(
    values: np.ndarray,
    *,
    seed: int,
) -> np.ndarray:
    """Shuffle ``values`` with ``np.random.default_rng(seed)`` (D-S040-20)."""
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(int(seed))
    return array[rng.permutation(array.shape[0])]


def regression_statistical_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> StatisticalMetrics:
    """RMSE, MAE, R², Spearman rank IC, Pearson IC."""
    target = _finite_vector(y_true, name="y_true")
    predicted = _finite_vector(y_pred, name="y_pred")
    _require_aligned(target, predicted)
    residual = target - predicted
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    mae = float(np.mean(np.abs(residual)))
    return StatisticalMetrics(
        rmse=rmse,
        mae=mae,
        r_squared=_r_squared(target, predicted),
        spearman_ic=_spearman(target, predicted),
        pearson_ic=_pearson(target, predicted),
    )


def classification_statistical_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    *,
    threshold: float,
) -> StatisticalMetrics:
    """Accuracy, balanced accuracy, ROC AUC, PR AUC, log loss, Brier, calibration bins."""
    target = _finite_vector(y_true, name="y_true")
    predicted_scores = _finite_vector(scores, name="y_score")
    _require_aligned(target, predicted_scores)
    predicted_positive = predicted_scores >= threshold
    actual_positive = target >= 0.5
    accuracy = float(np.mean(predicted_positive == actual_positive))
    return StatisticalMetrics(
        accuracy=accuracy,
        balanced_accuracy=_balanced_accuracy(actual_positive, predicted_positive),
        roc_auc=_roc_auc(actual_positive, predicted_scores),
        pr_auc=_average_precision(actual_positive, predicted_scores),
        log_loss=_log_loss(actual_positive, predicted_scores),
        brier_score=float(
            np.mean(np.square(predicted_scores - actual_positive.astype(np.float64)))
        ),
        calibration_bins=_calibration_bins(actual_positive, predicted_scores),
    )


def finance_metrics(
    scores: np.ndarray,
    forward_return: np.ndarray,
    *,
    threshold: float,
) -> FinanceMetrics:
    """Decile buckets, spread, hit rate, coverage, selected vs all — TEST/OOS only."""
    predicted_scores = _finite_vector(scores, name="y_score")
    returns = _finite_vector(forward_return, name="forward_return")
    _require_aligned(predicted_scores, returns)
    decile_means = _mean_return_by_decile(predicted_scores, returns)
    selected = predicted_scores >= threshold
    selected_returns = returns[selected]
    hit_rate: float | None
    mean_selected: float | None
    if selected_returns.size == 0:
        hit_rate = None
        mean_selected = None
    else:
        hit_rate = float(np.mean(selected_returns > 0.0))
        mean_selected = float(np.mean(selected_returns))
    return FinanceMetrics(
        mean_forward_return_by_decile=decile_means,
        top_bottom_spread=_optional_subtract(decile_means[DECILE_COUNT - 1], decile_means[0]),
        hit_rate=hit_rate,
        coverage=float(np.mean(selected)),
        mean_forward_return_selected=mean_selected,
        mean_forward_return_all=float(np.mean(returns)),
    )


def _metrics_for_sources(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    forward_return: np.ndarray,
    fold_ids: np.ndarray,
    train_targets_by_fold: Mapping[int, np.ndarray],
    task_type: TaskType,
    seed: int,
    threshold: float,
) -> dict[str, SourceMetrics]:
    payload = {
        MetricSource.MODEL.value: _source_metrics(
            y_true=y_true,
            y_pred=y_pred,
            scores=scores,
            forward_return=forward_return,
            task_type=task_type,
            threshold=threshold,
        )
    }
    for baseline in reference_baselines_for(task_type):
        baseline_pred, baseline_scores = _baseline_predictions(
            baseline,
            y_pred=y_pred,
            scores=scores,
            fold_ids=fold_ids,
            train_targets_by_fold=train_targets_by_fold,
            seed=seed,
        )
        payload[baseline.value] = _source_metrics(
            y_true=y_true,
            y_pred=baseline_pred,
            scores=baseline_scores,
            forward_return=forward_return,
            task_type=task_type,
            threshold=threshold,
        )
    return payload


def _source_metrics(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    forward_return: np.ndarray,
    task_type: TaskType,
    threshold: float,
) -> SourceMetrics:
    if task_type is TaskType.REGRESSION:
        statistical = regression_statistical_metrics(y_true, y_pred)
    else:
        statistical = classification_statistical_metrics(y_true, scores, threshold=threshold)
    return SourceMetrics(
        statistical=statistical,
        finance=finance_metrics(scores, forward_return, threshold=threshold),
    )


def _baseline_predictions(
    baseline: MetricSource,
    *,
    y_pred: np.ndarray,
    scores: np.ndarray,
    fold_ids: np.ndarray,
    train_targets_by_fold: Mapping[int, np.ndarray],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if baseline is MetricSource.RANDOM_PERMUTATION:
        return _permute_within_folds(y_pred, scores, fold_ids=fold_ids, seed=seed)
    baseline_pred = np.empty_like(y_pred, dtype=np.float64)
    baseline_scores = np.empty_like(scores, dtype=np.float64)
    for fold_id in np.unique(fold_ids):
        mask = fold_ids == fold_id
        train_y = np.asarray(train_targets_by_fold[int(fold_id)], dtype=np.float64)
        if train_y.size == 0:
            msg = f"fold {int(fold_id)} TRAIN targets are empty"
            raise ValidationError(msg)
        if baseline is MetricSource.CONSTANT_MEAN:
            fill = float(np.mean(train_y))
        else:
            fill = _majority_class(train_y)
        baseline_pred[mask] = fill
        baseline_scores[mask] = fill
    return baseline_pred, baseline_scores


def _permute_within_folds(
    y_pred: np.ndarray,
    scores: np.ndarray,
    *,
    fold_ids: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    shuffled_pred = np.array(y_pred, dtype=np.float64, copy=True)
    shuffled_scores = np.array(scores, dtype=np.float64, copy=True)
    for fold_id in np.unique(fold_ids):
        mask = fold_ids == int(fold_id)
        order = np.random.default_rng(int(seed)).permutation(int(mask.sum()))
        shuffled_pred[mask] = shuffled_pred[mask][order]
        shuffled_scores[mask] = shuffled_scores[mask][order]
    return shuffled_pred, shuffled_scores


def _majority_class(train_y: np.ndarray) -> float:
    values, counts = np.unique(train_y, return_counts=True)
    return float(values[int(np.argmax(counts))])


def _decision_scores(
    task_type: TaskType,
    *,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> np.ndarray:
    if task_type is TaskType.CLASSIFICATION and np.all(np.isfinite(y_proba)):
        return y_proba
    return y_pred


def _require_prediction_columns(frame: pl.DataFrame) -> None:
    missing = [name for name in _REQUIRED_PREDICTION_COLUMNS if name not in frame.columns]
    if missing:
        msg = f"predictions missing required column: {missing[0]}"
        raise ValidationError(msg)


def _float_column(frame: pl.DataFrame, name: str) -> np.ndarray:
    return np.asarray(frame.get_column(name).to_list(), dtype=np.float64)


def _finite_vector(values: np.ndarray, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size == 0:
        msg = f"{name} must be non-empty"
        raise ValidationError(msg)
    if not np.all(np.isfinite(array)):
        msg = f"{name} must be finite"
        raise ValidationError(msg)
    return array


def _require_aligned(left: np.ndarray, right: np.ndarray) -> None:
    if left.shape[0] != right.shape[0]:
        msg = "metric arrays must have the same length"
        raise ValidationError(msg)


def _r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    residual_sum = float(np.sum(np.square(y_true - y_pred)))
    total_sum = float(np.sum(np.square(y_true - np.mean(y_true))))
    if total_sum == 0.0:
        return 1.0 if residual_sum == 0.0 else 0.0
    return 1.0 - residual_sum / total_sum


def _pearson(left: np.ndarray, right: np.ndarray) -> float | None:
    centered_left = left - np.mean(left)
    centered_right = right - np.mean(right)
    denominator = float(
        np.sqrt(np.sum(np.square(centered_left)) * np.sum(np.square(centered_right)))
    )
    if denominator == 0.0:
        return None
    return float(np.sum(centered_left * centered_right) / denominator)


def _spearman(left: np.ndarray, right: np.ndarray) -> float | None:
    return _pearson(_average_ranks(left), _average_ranks(right))


def _average_ranks(values: np.ndarray) -> np.ndarray:
    n = values.shape[0]
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(n, dtype=np.float64)
    index = 0
    while index < n:
        end = index + 1
        while end < n and sorted_values[end] == sorted_values[index]:
            end += 1
        average = 0.5 * (index + 1 + end)
        ranks[order[index:end]] = average
        index = end
    return ranks


def _balanced_accuracy(actual_positive: np.ndarray, predicted_positive: np.ndarray) -> float | None:
    n_pos = int(actual_positive.sum())
    n_neg = int((~actual_positive).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    tpr = float(np.mean(predicted_positive[actual_positive]))
    tnr = float(np.mean(~predicted_positive[~actual_positive]))
    return 0.5 * (tpr + tnr)


def _roc_auc(actual_positive: np.ndarray, scores: np.ndarray) -> float | None:
    n_pos = int(actual_positive.sum())
    n_neg = int((~actual_positive).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = _average_ranks(scores)
    sum_positive_ranks = float(ranks[actual_positive].sum())
    return (sum_positive_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _average_precision(actual_positive: np.ndarray, scores: np.ndarray) -> float | None:
    n_pos = int(actual_positive.sum())
    if n_pos == 0:
        return None
    order = np.argsort(-scores, kind="mergesort")
    sorted_positive = actual_positive[order]
    true_positives = np.cumsum(sorted_positive.astype(np.float64))
    precision = true_positives / np.arange(1, sorted_positive.shape[0] + 1, dtype=np.float64)
    return float(precision[sorted_positive].sum() / n_pos)


def _log_loss(actual_positive: np.ndarray, scores: np.ndarray) -> float:
    clipped = np.clip(scores, _LOG_LOSS_EPS, 1.0 - _LOG_LOSS_EPS)
    labels = actual_positive.astype(np.float64)
    return float(-np.mean(labels * np.log(clipped) + (1.0 - labels) * np.log(1.0 - clipped)))


def _calibration_bins(
    actual_positive: np.ndarray,
    scores: np.ndarray,
) -> tuple[CalibrationBin, ...]:
    clipped = np.clip(scores, 0.0, 1.0)
    bin_index = np.minimum(
        (clipped * CALIBRATION_BIN_COUNT).astype(np.int64), CALIBRATION_BIN_COUNT - 1
    )
    bins: list[CalibrationBin] = []
    for index in range(CALIBRATION_BIN_COUNT):
        lower = index / CALIBRATION_BIN_COUNT
        upper = (index + 1) / CALIBRATION_BIN_COUNT
        mask = bin_index == index
        count = int(mask.sum())
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
                mean_predicted=float(np.mean(clipped[mask])),
                mean_observed=float(np.mean(actual_positive[mask].astype(np.float64))),
            )
        )
    return tuple(bins)


def _mean_return_by_decile(
    scores: np.ndarray,
    forward_return: np.ndarray,
) -> tuple[float | None, ...]:
    n = scores.shape[0]
    order = np.argsort(scores, kind="mergesort")
    decile_ids = np.empty(n, dtype=np.int64)
    for position, row_index in enumerate(order):
        decile_ids[row_index] = min(DECILE_COUNT, position * DECILE_COUNT // n + 1)
    means: list[float | None] = []
    for decile in range(1, DECILE_COUNT + 1):
        mask = decile_ids == decile
        if not np.any(mask):
            means.append(None)
            continue
        means.append(float(np.mean(forward_return[mask])))
    return tuple(means)


def _optional_subtract(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "expected a finite number or null"
        raise ValidationError(msg)
    number = float(value)
    if not np.isfinite(number):
        return None
    return number


def _freeze_source_metrics(values: Mapping[str, SourceMetrics]) -> Mapping[str, SourceMetrics]:
    return MappingProxyType(dict(values))


def _freeze_fold_metrics(
    values: Mapping[str, Mapping[str, SourceMetrics]],
) -> Mapping[str, Mapping[str, SourceMetrics]]:
    return MappingProxyType(
        {fold_id: _freeze_source_metrics(sources) for fold_id, sources in values.items()}
    )
