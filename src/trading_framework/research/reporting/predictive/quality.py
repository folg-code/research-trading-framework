"""Quality diagnostic flags for Predictive Research reports.

Flags are warnings with declared thresholds. They never block rendering and
never convert into a PASS/FAIL verdict (SPRINT_041 §4.9).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.metrics import (
    MetricSource,
    PredictiveMetricsReport,
    StatisticalMetrics,
)
from trading_framework.research.predictive.splitting import FoldRole


class PredictiveQualityFlag(StrEnum):
    """Diagnostic warning codes — not validation verdicts."""

    SMALL_TEST_SAMPLE = "SMALL_TEST_SAMPLE"
    SEVERE_CLASS_IMBALANCE = "SEVERE_CLASS_IMBALANCE"
    UNSTABLE_ACROSS_FOLDS = "UNSTABLE_ACROSS_FOLDS"
    WITHIN_PERMUTATION_SPREAD = "WITHIN_PERMUTATION_SPREAD"
    HIGH_EXCLUSION_SHARE = "HIGH_EXCLUSION_SHARE"
    SINGLE_FOLD_DOMINANCE = "SINGLE_FOLD_DOMINANCE"
    POOR_CALIBRATION = "POOR_CALIBRATION"
    LARGE_TRAIN_TEST_GAP = "LARGE_TRAIN_TEST_GAP"


@dataclass(frozen=True, slots=True)
class PredictiveQualityWarning:
    """One read-only quality diagnostic with the threshold that triggered it."""

    code: PredictiveQualityFlag
    message: str
    threshold: float
    observed: float
    fold_id: int | None = None


@dataclass(frozen=True, slots=True)
class PredictiveReportQualityRules:
    """Declared thresholds for report quality flags (D-S041-06)."""

    min_test_rows: int = 30
    min_minority_class_share: float = 0.10
    max_fold_metric_spread: float = 0.15
    max_exclusion_share: float = 0.40
    max_single_fold_test_share: float = 0.60
    max_calibration_abs_error: float = 0.15
    max_train_test_gap: float = 0.20

    def __post_init__(self) -> None:
        if self.min_test_rows < 1:
            msg = "min_test_rows must be >= 1"
            raise ValidationError(msg)
        for name in (
            "min_minority_class_share",
            "max_fold_metric_spread",
            "max_exclusion_share",
            "max_single_fold_test_share",
            "max_calibration_abs_error",
            "max_train_test_gap",
        ):
            value = float(getattr(self, name))
            if value < 0.0:
                msg = f"{name} must be >= 0"
                raise ValidationError(msg)


def primary_metric_name(task_type: TaskType) -> str:
    """Return the primary metric field used for stability and permutation flags."""
    if task_type is TaskType.CLASSIFICATION:
        return "roc_auc"
    return "spearman_ic"


def primary_metric_value(stats: StatisticalMetrics, task_type: TaskType) -> float | None:
    """Read the primary metric from statistical scores."""
    if task_type is TaskType.CLASSIFICATION:
        return stats.roc_auc
    return stats.spearman_ic


def evaluate_predictive_quality_flags(
    *,
    metrics: PredictiveMetricsReport,
    test_rows_by_fold: dict[int, int],
    test_labels: tuple[float, ...],
    exclusion_counts: dict[str, int],
    role_counts: dict[str, int],
    rules: PredictiveReportQualityRules | None = None,
) -> tuple[PredictiveQualityWarning, ...]:
    """Evaluate declared rules against persisted metrics and counts."""
    quality = rules or PredictiveReportQualityRules()
    warnings: list[PredictiveQualityWarning] = []
    task_type = metrics.task_type
    metric_name = primary_metric_name(task_type)

    for fold_id, count in sorted(test_rows_by_fold.items()):
        if count < quality.min_test_rows:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.SMALL_TEST_SAMPLE,
                    message=(
                        f"Fold {fold_id} has {count} TEST rows (threshold {quality.min_test_rows})."
                    ),
                    threshold=float(quality.min_test_rows),
                    observed=float(count),
                    fold_id=fold_id,
                )
            )

    if task_type is TaskType.CLASSIFICATION and test_labels:
        positives = sum(1 for value in test_labels if value > 0.0)
        share = min(positives, len(test_labels) - positives) / len(test_labels)
        if share < quality.min_minority_class_share:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.SEVERE_CLASS_IMBALANCE,
                    message=(
                        f"Minority class share is {share:.1%} "
                        f"(threshold {quality.min_minority_class_share:.1%})."
                    ),
                    threshold=quality.min_minority_class_share,
                    observed=share,
                )
            )

    fold_values = [
        primary_metric_value(sources[MetricSource.MODEL.value].statistical, task_type)
        for _fold_id, sources in sorted(metrics.folds.items(), key=lambda item: int(item[0]))
    ]
    present = [value for value in fold_values if value is not None]
    if len(present) >= 2:
        spread = max(present) - min(present)
        if spread > quality.max_fold_metric_spread:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.UNSTABLE_ACROSS_FOLDS,
                    message=(
                        f"Per-fold {metric_name} spread is {spread:.3f} "
                        f"(threshold {quality.max_fold_metric_spread:.3f})."
                    ),
                    threshold=quality.max_fold_metric_spread,
                    observed=spread,
                )
            )

    model_pooled = primary_metric_value(
        metrics.pooled[MetricSource.MODEL.value].statistical, task_type
    )
    permutation = metrics.pooled.get(MetricSource.RANDOM_PERMUTATION.value)
    permutation_value = (
        None if permutation is None else primary_metric_value(permutation.statistical, task_type)
    )
    if (
        model_pooled is not None
        and permutation_value is not None
        and model_pooled <= permutation_value
    ):
        warnings.append(
            PredictiveQualityWarning(
                code=PredictiveQualityFlag.WITHIN_PERMUTATION_SPREAD,
                message=(
                    f"Pooled {metric_name} {model_pooled:.3f} does not exceed "
                    f"the permutation baseline {permutation_value:.3f}."
                ),
                threshold=permutation_value,
                observed=model_pooled,
            )
        )

    candidate = int(exclusion_counts.get("candidate_rows", 0))
    dropped = (
        int(exclusion_counts.get("incomplete_horizon", 0))
        + int(exclusion_counts.get("insufficient_data", 0))
        + int(exclusion_counts.get("null_features", 0))
    )
    if candidate > 0:
        build_share = dropped / candidate
        if build_share > quality.max_exclusion_share:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.HIGH_EXCLUSION_SHARE,
                    message=(
                        f"Build exclusions removed {build_share:.1%} of candidate rows "
                        f"(threshold {quality.max_exclusion_share:.1%})."
                    ),
                    threshold=quality.max_exclusion_share,
                    observed=build_share,
                )
            )

    total_role_rows = sum(int(count) for count in role_counts.values())
    guard_rows = int(role_counts.get(FoldRole.PURGED.value, 0)) + int(
        role_counts.get(FoldRole.EMBARGOED.value, 0)
    )
    if total_role_rows > 0:
        guard_share = guard_rows / total_role_rows
        if guard_share > quality.max_exclusion_share:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.HIGH_EXCLUSION_SHARE,
                    message=(
                        f"Purge and embargo retained {guard_share:.1%} of fold-assigned rows "
                        f"(threshold {quality.max_exclusion_share:.1%})."
                    ),
                    threshold=quality.max_exclusion_share,
                    observed=guard_share,
                )
            )

    total_test = sum(test_rows_by_fold.values())
    if total_test > 0:
        dominant_fold, dominant_count = max(test_rows_by_fold.items(), key=lambda item: item[1])
        share = dominant_count / total_test
        if share > quality.max_single_fold_test_share:
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.SINGLE_FOLD_DOMINANCE,
                    message=(
                        f"Fold {dominant_fold} holds {share:.1%} of TEST rows "
                        f"(threshold {quality.max_single_fold_test_share:.1%})."
                    ),
                    threshold=quality.max_single_fold_test_share,
                    observed=share,
                    fold_id=dominant_fold,
                )
            )

    if task_type is TaskType.CLASSIFICATION:
        bins = metrics.pooled[MetricSource.MODEL.value].statistical.calibration_bins
        occupied = [
            abs(float(bin_.mean_predicted) - float(bin_.mean_observed))
            for bin_ in bins
            if bin_.count > 0 and bin_.mean_predicted is not None and bin_.mean_observed is not None
        ]
        if occupied:
            abs_error = sum(occupied) / len(occupied)
            if abs_error > quality.max_calibration_abs_error:
                warnings.append(
                    PredictiveQualityWarning(
                        code=PredictiveQualityFlag.POOR_CALIBRATION,
                        message=(
                            f"Mean |predicted-observed| across calibration bins is "
                            f"{abs_error:.3f} (threshold {quality.max_calibration_abs_error:.3f})."
                        ),
                        threshold=quality.max_calibration_abs_error,
                        observed=abs_error,
                    )
                )

    fold_primary = metrics.fold_primary or {}
    for fold_key, values in sorted(fold_primary.items(), key=lambda item: int(item[0])):
        gap = values.get("primary_gap")
        if gap is None:
            continue
        observed = abs(float(gap))
        if observed > quality.max_train_test_gap:
            fold_id = int(fold_key)
            warnings.append(
                PredictiveQualityWarning(
                    code=PredictiveQualityFlag.LARGE_TRAIN_TEST_GAP,
                    message=(
                        f"Fold {fold_id} |train - test| on {metric_name} is {observed:.3f} "
                        f"(threshold {quality.max_train_test_gap:.3f})."
                    ),
                    threshold=quality.max_train_test_gap,
                    observed=observed,
                    fold_id=fold_id,
                )
            )

    return tuple(warnings)
