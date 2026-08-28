"""View models for the Predictive Research dashboard page (S044-T004-T010).

Reads persisted JSON sidecars only (D-S044-09): ``metrics.json``,
``importance.json``, ``learning_curves.json``, ``window_accounting.json``.
Never recomputes a research metric — a number not already in one of these
files is a gap to close upstream, not in this module.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_app.catalog import (
    list_predictive_catalog,
    load_predictive_run_identity,
)
from dashboard_app.contracts import (
    PredictiveBucketView,
    PredictiveCalibrationBinView,
    PredictiveDatasetSummary,
    PredictiveFoldMetricRow,
    PredictiveImportanceRow,
    PredictiveLearningCurveView,
    PredictiveRunSummary,
)
from dashboard_app.formatting import format_created_at

REPORT_HTML_FILENAME = "report.html"
METRICS_FILENAME = "metrics.json"
IMPORTANCE_FILENAME = "importance.json"
LEARNING_CURVES_FILENAME = "learning_curves.json"
WINDOW_ACCOUNTING_FILENAME = "window_accounting.json"


def list_predictive_datasets(storage_root: Path) -> tuple[PredictiveDatasetSummary, ...]:
    """Return predictive dataset envelopes, newest first (study picker rows)."""
    return list_predictive_catalog(storage_root).datasets


def runs_for_dataset(
    runs: Sequence[PredictiveRunSummary], dataset_fingerprint: str
) -> tuple[PredictiveRunSummary, ...]:
    """Filter runs to one study, grouped by dataset fingerprint (D-S044-06)."""
    return tuple(run for run in runs if run.dataset_fingerprint == dataset_fingerprint)


def sort_leaderboard(runs: Sequence[PredictiveRunSummary]) -> tuple[PredictiveRunSummary, ...]:
    """Sort runs by baseline delta descending; missing delta sorts last (D-S044-07)."""
    with_delta = [run for run in runs if run.baseline_delta is not None]
    without_delta = [run for run in runs if run.baseline_delta is None]
    with_delta.sort(key=lambda run: run.baseline_delta, reverse=True)  # type: ignore[arg-type,return-value]
    without_delta.sort(
        key=lambda run: (
            run.created_at_utc.isoformat() if run.created_at_utc is not None else "",
            run.run_id,
        ),
        reverse=True,
    )
    return tuple(with_delta) + tuple(without_delta)


@dataclass(frozen=True, slots=True)
class LeaderboardRowView:
    """One display-ready leaderboard row (D-S044-07)."""

    run_id: str
    created_at: str
    family: str
    primary_metric_label: str
    primary_metric_display: str
    baseline_delta_display: str
    baseline_delta: float | None
    missing_baseline: bool
    quality_flag_codes: tuple[str, ...]
    has_metrics: bool


def build_leaderboard_rows(runs: Sequence[PredictiveRunSummary]) -> tuple[LeaderboardRowView, ...]:
    """Build sorted, display-ready leaderboard rows for one study."""
    rows: list[LeaderboardRowView] = []
    for run in sort_leaderboard(runs):
        missing_baseline = (
            run.has_metrics and run.primary_metric_value is not None and run.baseline_delta is None
        )
        rows.append(
            LeaderboardRowView(
                run_id=run.run_id,
                created_at=format_created_at(run.created_at_utc),
                family=run.family or "—",
                primary_metric_label=run.primary_metric_name or "—",
                primary_metric_display=_format_metric(run.primary_metric_value),
                baseline_delta_display=_format_delta(run.baseline_delta),
                baseline_delta=run.baseline_delta,
                missing_baseline=missing_baseline,
                quality_flag_codes=tuple(flag.code for flag in run.quality_flags),
                has_metrics=run.has_metrics,
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class RunMetricsView:
    """Run detail metrics view model: per-fold rows plus pooled context (AC3)."""

    task_type: str | None
    primary_metric_name: str | None
    pooled_model_value: float | None
    pooled_permutation_value: float | None
    baseline_delta: float | None
    fold_rows: tuple[PredictiveFoldMetricRow, ...]
    calibration_bins: tuple[PredictiveCalibrationBinView, ...]
    bucket_rows: tuple[PredictiveBucketView, ...]
    top_bottom_spread: float | None
    hit_rate: float | None


def load_run_metrics(storage_path: str | Path) -> dict[str, Any] | None:
    """Load ``metrics.json`` for one run, if present and valid."""
    return _read_json_object(Path(storage_path) / METRICS_FILENAME)


def build_run_metrics_view(metrics: Mapping[str, Any] | None) -> RunMetricsView | None:
    """Build the run-detail metrics view model from a parsed ``metrics.json``."""
    if metrics is None:
        return None
    task_type_raw = metrics.get("task_type")
    task_type = str(task_type_raw) if isinstance(task_type_raw, str) else None
    metric_name = (
        "roc_auc"
        if task_type == "CLASSIFICATION"
        else "spearman_ic"
        if task_type == "REGRESSION"
        else None
    )

    pooled = metrics.get("pooled")
    pooled = pooled if isinstance(pooled, dict) else {}
    pooled_model = pooled.get("MODEL")
    pooled_permutation = pooled.get("RANDOM_PERMUTATION")

    pooled_model_value = _statistical_value(pooled_model, metric_name) if metric_name else None
    pooled_permutation_value = (
        _statistical_value(pooled_permutation, metric_name) if metric_name else None
    )
    baseline_delta = (
        None
        if pooled_model_value is None or pooled_permutation_value is None
        else pooled_model_value - pooled_permutation_value
    )

    folds_raw = metrics.get("folds")
    folds_raw = folds_raw if isinstance(folds_raw, dict) else {}
    fold_primary_raw = metrics.get("fold_primary")
    fold_primary_raw = fold_primary_raw if isinstance(fold_primary_raw, dict) else {}

    fold_rows: list[PredictiveFoldMetricRow] = []
    for fold_id in sorted(folds_raw, key=str):
        source = folds_raw[fold_id]
        if not isinstance(source, dict):
            continue
        model_value = _statistical_value(source.get("MODEL"), metric_name) if metric_name else None
        permutation_value = (
            _statistical_value(source.get("RANDOM_PERMUTATION"), metric_name)
            if metric_name
            else None
        )
        gap = fold_primary_raw.get(str(fold_id))
        gap = gap if isinstance(gap, dict) else {}
        fold_rows.append(
            PredictiveFoldMetricRow(
                fold_id=str(fold_id),
                model_value=model_value,
                permutation_value=permutation_value,
                train_primary=_optional_float(gap.get("train_primary")),
                test_primary=_optional_float(gap.get("test_primary")),
                primary_gap=_optional_float(gap.get("primary_gap")),
            )
        )

    calibration_bins = _build_calibration_bins(pooled_model)
    bucket_rows, top_bottom_spread, hit_rate = _build_bucket_rows(pooled_model)

    return RunMetricsView(
        task_type=task_type,
        primary_metric_name=metric_name,
        pooled_model_value=pooled_model_value,
        pooled_permutation_value=pooled_permutation_value,
        baseline_delta=baseline_delta,
        fold_rows=tuple(fold_rows),
        calibration_bins=calibration_bins,
        bucket_rows=bucket_rows,
        top_bottom_spread=top_bottom_spread,
        hit_rate=hit_rate,
    )


def load_run_importance(storage_path: str | Path) -> dict[str, Any] | None:
    """Load ``importance.json`` for one run, if present (T007 — optional sidecar)."""
    return _read_json_object(Path(storage_path) / IMPORTANCE_FILENAME)


def build_importance_view(
    importance: Mapping[str, Any] | None,
) -> tuple[PredictiveImportanceRow, ...]:
    """Average permutation importance across folds, one row per feature.

    Degrades to an empty tuple when the sidecar is missing or empty (AC4) —
    callers skip the panel rather than rendering nothing meaningful.
    """
    if not importance:
        return ()
    folds_raw = importance.get("folds")
    if not isinstance(folds_raw, list) or not folds_raw:
        return ()

    totals: dict[str, list[float]] = {}
    stds: dict[str, list[float]] = {}
    for fold in folds_raw:
        if not isinstance(fold, dict):
            continue
        permutation = fold.get("permutation")
        if not isinstance(permutation, dict):
            continue
        names = permutation.get("feature_names")
        means = permutation.get("importances_mean")
        std_values = permutation.get("importances_std")
        if not isinstance(names, list) or not isinstance(means, list):
            continue
        for index, name in enumerate(names):
            if not isinstance(name, str) or index >= len(means):
                continue
            mean_value = means[index]
            if not isinstance(mean_value, (int, float)):
                continue
            totals.setdefault(name, []).append(float(mean_value))
            if isinstance(std_values, list) and index < len(std_values):
                std_value = std_values[index]
                if isinstance(std_value, (int, float)):
                    stds.setdefault(name, []).append(float(std_value))

    rows = [
        PredictiveImportanceRow(
            feature_name=name,
            mean_importance=sum(values) / len(values),
            std_importance=(sum(stds[name]) / len(stds[name])) if stds.get(name) else 0.0,
        )
        for name, values in totals.items()
    ]
    return tuple(sorted(rows, key=lambda row: row.mean_importance, reverse=True))


def load_run_learning_curves(storage_path: str | Path) -> dict[str, Any] | None:
    """Load ``learning_curves.json`` for one run, if present (optional sidecar)."""
    return _read_json_object(Path(storage_path) / LEARNING_CURVES_FILENAME)


def build_learning_curves_view(
    payload: Mapping[str, Any] | None,
) -> tuple[PredictiveLearningCurveView, ...]:
    """Build fold learning-curve rows; degrades to empty when absent/malformed."""
    if not payload:
        return ()
    folds_raw = payload.get("folds")
    if not isinstance(folds_raw, list):
        return ()
    rows: list[PredictiveLearningCurveView] = []
    for fold in folds_raw:
        if not isinstance(fold, dict):
            continue
        epochs = fold.get("epochs")
        train_loss = fold.get("train_loss")
        validation_loss = fold.get("validation_loss")
        fold_id = fold.get("fold_id")
        stopping_epoch = fold.get("stopping_epoch")
        if (
            not isinstance(epochs, list)
            or not isinstance(train_loss, list)
            or not isinstance(validation_loss, list)
        ):
            continue
        if not isinstance(fold_id, int) or not isinstance(stopping_epoch, int):
            continue
        rows.append(
            PredictiveLearningCurveView(
                fold_id=fold_id,
                epochs=tuple(int(value) for value in epochs),
                train_loss=tuple(float(value) for value in train_loss),
                validation_loss=tuple(float(value) for value in validation_loss),
                stopping_epoch=stopping_epoch,
            )
        )
    return tuple(sorted(rows, key=lambda row: row.fold_id))


@dataclass(frozen=True, slots=True)
class WindowAccountingRow:
    """One fold/role window-accounting row (D-S043-10)."""

    fold_id: int
    fold_role: str
    candidate_end_rows: int
    windows_built: int
    windows_dropped_incomplete: int
    windows_dropped_gap: int
    windows_dropped_fold_boundary: int


def load_run_window_accounting(storage_path: str | Path) -> dict[str, Any] | None:
    """Load ``window_accounting.json`` for one run, if present (optional sidecar)."""
    return _read_json_object(Path(storage_path) / WINDOW_ACCOUNTING_FILENAME)


def build_window_accounting_rows(
    payload: Mapping[str, Any] | None,
) -> tuple[WindowAccountingRow, ...]:
    """Build window-accounting rows; degrades to empty when absent/malformed."""
    if not payload:
        return ()
    folds_raw = payload.get("folds")
    if not isinstance(folds_raw, list):
        return ()
    rows: list[WindowAccountingRow] = []
    for entry in folds_raw:
        if not isinstance(entry, dict):
            continue
        try:
            rows.append(
                WindowAccountingRow(
                    fold_id=int(entry["fold_id"]),
                    fold_role=str(entry["fold_role"]),
                    candidate_end_rows=int(entry["candidate_end_rows"]),
                    windows_built=int(entry["windows_built"]),
                    windows_dropped_incomplete=int(entry["windows_dropped_incomplete"]),
                    windows_dropped_gap=int(entry["windows_dropped_gap"]),
                    windows_dropped_fold_boundary=int(entry["windows_dropped_fold_boundary"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class ProvenanceView:
    """Dataset fingerprint, estimator spec, seeds, library and version (AC5)."""

    dataset_fingerprint: str | None
    run_fingerprint: str | None
    estimator_family: str | None
    estimator_seed: int | None
    task_type: str | None
    preprocessing_spec: Mapping[str, Any] | None
    library: str | None
    library_version: str | None
    framework_version: str | None


def load_run_provenance(storage_root: Path, run_id: str) -> ProvenanceView | None:
    """Build the provenance panel view model from the run manifest identity."""
    identity = load_predictive_run_identity(storage_root, run_id)
    if identity is None:
        return None
    estimator_spec = identity.get("estimator_spec")
    estimator_spec = estimator_spec if isinstance(estimator_spec, dict) else {}
    preprocessing_spec = identity.get("preprocessing_spec")
    seed = estimator_spec.get("seed")
    return ProvenanceView(
        dataset_fingerprint=_optional_str(identity.get("dataset_fingerprint")),
        run_fingerprint=_optional_str(identity.get("run_fingerprint")),
        estimator_family=_optional_str(estimator_spec.get("family")),
        estimator_seed=int(seed) if isinstance(seed, (int, float)) else None,
        task_type=_optional_str(estimator_spec.get("task_type")),
        preprocessing_spec=preprocessing_spec if isinstance(preprocessing_spec, dict) else None,
        library=_optional_str(identity.get("library")),
        library_version=_optional_str(identity.get("library_version")),
        framework_version=_optional_str(identity.get("framework_version")),
    )


def report_html_path(storage_path: str | Path) -> Path | None:
    """Return the run's offline HTML report path if it exists, else ``None`` (T008)."""
    path = Path(storage_path) / REPORT_HTML_FILENAME
    return path if path.is_file() else None


def _build_calibration_bins(pooled_model: Any) -> tuple[PredictiveCalibrationBinView, ...]:
    if not isinstance(pooled_model, dict):
        return ()
    statistical = pooled_model.get("statistical")
    if not isinstance(statistical, dict):
        return ()
    bins_raw = statistical.get("calibration_bins")
    if not isinstance(bins_raw, list):
        return ()
    rows: list[PredictiveCalibrationBinView] = []
    for entry in bins_raw:
        if not isinstance(entry, dict):
            continue
        try:
            rows.append(
                PredictiveCalibrationBinView(
                    bin_index=int(entry["bin_index"]),
                    lower=_optional_float(entry.get("lower")),
                    upper=_optional_float(entry.get("upper")),
                    count=int(entry.get("count", 0) or 0),
                    mean_predicted=_optional_float(entry.get("mean_predicted")),
                    mean_observed=_optional_float(entry.get("mean_observed")),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(sorted(rows, key=lambda row: row.bin_index))


def _build_bucket_rows(
    pooled_model: Any,
) -> tuple[tuple[PredictiveBucketView, ...], float | None, float | None]:
    if not isinstance(pooled_model, dict):
        return (), None, None
    finance = pooled_model.get("finance")
    if not isinstance(finance, dict):
        return (), None, None
    deciles = finance.get("mean_forward_return_by_decile")
    if not isinstance(deciles, list) or not deciles:
        return (), None, None
    rows = tuple(
        PredictiveBucketView(decile=index, mean_forward_return=_optional_float(value))
        for index, value in enumerate(deciles)
    )
    return (
        rows,
        _optional_float(finance.get("top_bottom_spread")),
        _optional_float(finance.get("hit_rate")),
    )


def _statistical_value(source: Any, metric_name: str | None) -> float | None:
    if metric_name is None or not isinstance(source, dict):
        return None
    statistical = source.get("statistical")
    if not isinstance(statistical, dict):
        return None
    value = statistical.get(metric_name)
    return float(value) if isinstance(value, (int, float)) else None


def _format_metric(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _format_delta(value: float | None) -> str:
    if value is None:
        return "no baseline"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.3f}"


def _optional_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload
