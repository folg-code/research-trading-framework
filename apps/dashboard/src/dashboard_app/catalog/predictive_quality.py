"""Dashboard-local Predictive Research quality flags and leaderboard metrics.

Mirrors the thresholds and codes of ``PredictiveReportQualityRules`` /
``evaluate_predictive_quality_flags`` (``trading_framework.research.reporting
.predictive.quality``) without importing ``trading_framework`` (ADR-0022).
Every function here reads only already-parsed JSON dicts (dataset
``manifest.json`` and run ``metrics.json``) — never ``predictions.parquet``.

Flags are warnings; they never become a PASS/FAIL verdict (D-S044-08).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dashboard_app.contracts import PredictiveQualityFlagView

MIN_TEST_ROWS = 30
MIN_MINORITY_CLASS_SHARE = 0.10
MAX_FOLD_METRIC_SPREAD = 0.15
MAX_EXCLUSION_SHARE = 0.40
MAX_SINGLE_FOLD_TEST_SHARE = 0.60
MAX_CALIBRATION_ABS_ERROR = 0.15
MAX_TRAIN_TEST_GAP = 0.20

SMALL_TEST_SAMPLE = "SMALL_TEST_SAMPLE"
UNSTABLE_ACROSS_FOLDS = "UNSTABLE_ACROSS_FOLDS"
WITHIN_PERMUTATION_SPREAD = "WITHIN_PERMUTATION_SPREAD"
HIGH_EXCLUSION_SHARE = "HIGH_EXCLUSION_SHARE"
SINGLE_FOLD_DOMINANCE = "SINGLE_FOLD_DOMINANCE"
LARGE_TRAIN_TEST_GAP = "LARGE_TRAIN_TEST_GAP"
POOR_CALIBRATION = "POOR_CALIBRATION"


@dataclass(frozen=True, slots=True)
class PredictiveMetricSelection:
    """Primary metric name/value and baseline delta for one run (D-S044-07)."""

    task_type: str | None
    primary_metric_name: str | None
    primary_metric_value: float | None
    baseline_delta: float | None


def _primary_metric_name(task_type: str | None) -> str | None:
    if task_type == "CLASSIFICATION":
        return "roc_auc"
    if task_type == "REGRESSION":
        return "spearman_ic"
    return None


def _statistical_value(source: Any, metric_name: str) -> float | None:
    if not isinstance(source, dict):
        return None
    statistical = source.get("statistical")
    if not isinstance(statistical, dict):
        return None
    value = statistical.get(metric_name)
    return float(value) if isinstance(value, (int, float)) else None


def select_primary_metric(metrics: dict[str, Any]) -> PredictiveMetricSelection:
    """Compute the primary metric and baseline delta from a parsed ``metrics.json``."""
    task_type = metrics.get("task_type")
    task_type_str = str(task_type) if isinstance(task_type, str) else None
    metric_name = _primary_metric_name(task_type_str)
    if metric_name is None:
        return PredictiveMetricSelection(
            task_type=task_type_str,
            primary_metric_name=None,
            primary_metric_value=None,
            baseline_delta=None,
        )
    pooled = metrics.get("pooled")
    pooled = pooled if isinstance(pooled, dict) else {}
    model_value = _statistical_value(pooled.get("MODEL"), metric_name)
    permutation_value = _statistical_value(pooled.get("RANDOM_PERMUTATION"), metric_name)
    baseline_delta = (
        None
        if model_value is None or permutation_value is None
        else model_value - permutation_value
    )
    return PredictiveMetricSelection(
        task_type=task_type_str,
        primary_metric_name=metric_name,
        primary_metric_value=model_value,
        baseline_delta=baseline_delta,
    )


def evaluate_predictive_quality_flags(
    *,
    dataset_manifest: dict[str, Any] | None,
    metrics: dict[str, Any] | None,
) -> tuple[PredictiveQualityFlagView, ...]:
    """Evaluate listing-local quality flags from persisted JSON only.

    Missing inputs skip the corresponding flag rather than failing the row
    (D-S044-08). ``SEVERE_CLASS_IMBALANCE`` is always skipped: minority-class
    counts are not persisted anywhere the listing reads.
    """
    flags: list[PredictiveQualityFlagView] = []
    fold_summary = (dataset_manifest or {}).get("fold_summary")
    fold_summary = fold_summary if isinstance(fold_summary, dict) else {}
    per_fold = fold_summary.get("per_fold")
    per_fold = per_fold if isinstance(per_fold, list) else []

    flags.extend(_small_test_sample_flags(per_fold))
    flags.extend(_single_fold_dominance_flag(per_fold))
    flags.extend(_high_exclusion_share_flags(dataset_manifest, fold_summary))

    if metrics is not None:
        selection = select_primary_metric(metrics)
        flags.extend(_unstable_across_folds_flag(metrics, selection))
        flags.extend(_within_permutation_spread_flag(selection))
        flags.extend(_poor_calibration_flag(metrics))
        flags.extend(_large_train_test_gap_flags(metrics))

    return tuple(flags)


def _small_test_sample_flags(per_fold: list[Any]) -> list[PredictiveQualityFlagView]:
    flags: list[PredictiveQualityFlagView] = []
    for entry in per_fold:
        if not isinstance(entry, dict):
            continue
        fold_id = entry.get("fold_id")
        test_count = entry.get("TEST")
        if not isinstance(test_count, (int, float)):
            continue
        if test_count < MIN_TEST_ROWS:
            flags.append(
                PredictiveQualityFlagView(
                    code=SMALL_TEST_SAMPLE,
                    message=(
                        f"Fold {fold_id} has {int(test_count)} TEST rows "
                        f"(threshold {MIN_TEST_ROWS})."
                    ),
                )
            )
    return flags


def _single_fold_dominance_flag(per_fold: list[Any]) -> list[PredictiveQualityFlagView]:
    counts = [
        (entry.get("fold_id"), entry.get("TEST"))
        for entry in per_fold
        if isinstance(entry, dict) and isinstance(entry.get("TEST"), (int, float))
    ]
    total = sum(count for _fold_id, count in counts)
    if total <= 0 or not counts:
        return []
    dominant_fold, dominant_count = max(counts, key=lambda item: item[1])
    share = dominant_count / total
    if share > MAX_SINGLE_FOLD_TEST_SHARE:
        return [
            PredictiveQualityFlagView(
                code=SINGLE_FOLD_DOMINANCE,
                message=(
                    f"Fold {dominant_fold} holds {share:.1%} of TEST rows "
                    f"(threshold {MAX_SINGLE_FOLD_TEST_SHARE:.1%})."
                ),
            )
        ]
    return []


def _high_exclusion_share_flags(
    dataset_manifest: dict[str, Any] | None, fold_summary: dict[str, Any]
) -> list[PredictiveQualityFlagView]:
    flags: list[PredictiveQualityFlagView] = []
    exclusion_counts = (dataset_manifest or {}).get("exclusion_counts")
    if isinstance(exclusion_counts, dict):
        candidate = int(exclusion_counts.get("candidate_rows", 0) or 0)
        dropped = sum(
            int(exclusion_counts.get(key, 0) or 0)
            for key in ("incomplete_horizon", "insufficient_data", "null_features")
        )
        if candidate > 0:
            share = dropped / candidate
            if share > MAX_EXCLUSION_SHARE:
                flags.append(
                    PredictiveQualityFlagView(
                        code=HIGH_EXCLUSION_SHARE,
                        message=(
                            f"Build exclusions removed {share:.1%} of candidate rows "
                            f"(threshold {MAX_EXCLUSION_SHARE:.1%})."
                        ),
                    )
                )

    role_counts = fold_summary.get("role_counts")
    if isinstance(role_counts, dict):
        total = sum(int(v or 0) for v in role_counts.values())
        guard = int(role_counts.get("PURGED", 0) or 0) + int(role_counts.get("EMBARGOED", 0) or 0)
        if total > 0:
            share = guard / total
            if share > MAX_EXCLUSION_SHARE:
                flags.append(
                    PredictiveQualityFlagView(
                        code=HIGH_EXCLUSION_SHARE,
                        message=(
                            f"Purge and embargo retained {share:.1%} of fold-assigned rows "
                            f"(threshold {MAX_EXCLUSION_SHARE:.1%})."
                        ),
                    )
                )
    return flags


def _unstable_across_folds_flag(
    metrics: dict[str, Any], selection: PredictiveMetricSelection
) -> list[PredictiveQualityFlagView]:
    metric_name = selection.primary_metric_name
    if metric_name is None:
        return []
    folds = metrics.get("folds")
    folds = folds if isinstance(folds, dict) else {}
    values: list[float] = []
    for source in folds.values():
        if not isinstance(source, dict):
            continue
        value = _statistical_value(source.get("MODEL"), metric_name)
        if value is not None:
            values.append(value)
    if len(values) < 2:
        return []
    spread = max(values) - min(values)
    if spread > MAX_FOLD_METRIC_SPREAD:
        return [
            PredictiveQualityFlagView(
                code=UNSTABLE_ACROSS_FOLDS,
                message=(
                    f"Per-fold {metric_name} spread is {spread:.3f} "
                    f"(threshold {MAX_FOLD_METRIC_SPREAD:.3f})."
                ),
            )
        ]
    return []


def _within_permutation_spread_flag(
    selection: PredictiveMetricSelection,
) -> list[PredictiveQualityFlagView]:
    if selection.primary_metric_value is None or selection.baseline_delta is None:
        return []
    if selection.baseline_delta <= 0:
        permutation_value = selection.primary_metric_value - selection.baseline_delta
        return [
            PredictiveQualityFlagView(
                code=WITHIN_PERMUTATION_SPREAD,
                message=(
                    f"Pooled {selection.primary_metric_name} {selection.primary_metric_value:.3f} "
                    f"does not exceed the permutation baseline {permutation_value:.3f}."
                ),
            )
        ]
    return []


def _poor_calibration_flag(metrics: dict[str, Any]) -> list[PredictiveQualityFlagView]:
    pooled = metrics.get("pooled")
    pooled = pooled if isinstance(pooled, dict) else {}
    model = pooled.get("MODEL")
    if not isinstance(model, dict):
        return []
    statistical = model.get("statistical")
    if not isinstance(statistical, dict):
        return []
    bins = statistical.get("calibration_bins")
    if not isinstance(bins, list) or not bins:
        return []
    errors = []
    for bin_ in bins:
        if not isinstance(bin_, dict):
            continue
        count = bin_.get("count")
        predicted = bin_.get("mean_predicted")
        observed = bin_.get("mean_observed")
        if not count or predicted is None or observed is None:
            continue
        errors.append(abs(float(predicted) - float(observed)))
    if not errors:
        return []
    abs_error = sum(errors) / len(errors)
    if abs_error > MAX_CALIBRATION_ABS_ERROR:
        return [
            PredictiveQualityFlagView(
                code=POOR_CALIBRATION,
                message=(
                    "Mean |predicted-observed| across calibration bins is "
                    f"{abs_error:.3f} (threshold {MAX_CALIBRATION_ABS_ERROR:.3f})."
                ),
            )
        ]
    return []


def _large_train_test_gap_flags(metrics: dict[str, Any]) -> list[PredictiveQualityFlagView]:
    fold_primary = metrics.get("fold_primary")
    fold_primary = fold_primary if isinstance(fold_primary, dict) else {}
    flags: list[PredictiveQualityFlagView] = []
    for fold_id, values in sorted(fold_primary.items(), key=lambda item: str(item[0])):
        if not isinstance(values, dict):
            continue
        gap = values.get("primary_gap")
        if gap is None:
            continue
        observed = abs(float(gap))
        if observed > MAX_TRAIN_TEST_GAP:
            flags.append(
                PredictiveQualityFlagView(
                    code=LARGE_TRAIN_TEST_GAP,
                    message=(
                        f"Fold {fold_id} |train - test| primary metric is {observed:.3f} "
                        f"(threshold {MAX_TRAIN_TEST_GAP:.3f})."
                    ),
                )
            )
    return flags
