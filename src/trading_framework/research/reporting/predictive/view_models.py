"""View models for Predictive Research HTML reports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.importance import ImportanceTrace
from trading_framework.research.predictive.leaderboard import PredictiveLeaderboard
from trading_framework.research.predictive.metrics import (
    CalibrationBin,
    MetricSource,
    PredictiveMetricsReport,
)
from trading_framework.research.predictive.selection import SelectionTrace
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.research.reporting.predictive.quality import (
    PredictiveQualityWarning,
    PredictiveReportQualityRules,
    evaluate_predictive_quality_flags,
    primary_metric_name,
    primary_metric_value,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.models.utc_instant import require_utc_aware


@dataclass(frozen=True, slots=True)
class FoldTimelineBand:
    """One TRAIN / PURGED / EMBARGOED / TEST span on the fold timeline."""

    fold_id: int
    role: str
    start: datetime
    end: datetime
    row_count: int


@dataclass(frozen=True, slots=True)
class FoldMetricSnapshot:
    """Per-fold primary metric for the model and each reference baseline."""

    fold_id: int
    test_rows: int
    model: float | None
    baselines: Mapping[str, float | None]


@dataclass(frozen=True, slots=True)
class FeatureImportanceBar:
    """Mean native gain and permutation drop for one feature across folds."""

    feature_name: str
    native_gain: float | None
    permutation_mean: float
    permutation_std: float


@dataclass(frozen=True, slots=True)
class LeaderboardDisplayRow:
    """One ranked estimator or baseline row for the leaderboard panel."""

    rank: int
    kind: str
    family: str
    source: str
    pooled_primary: float | None
    metric: str
    run_id: str


@dataclass(frozen=True, slots=True)
class SelectionCandidateScore:
    """One candidate's inner-validation score inside a displayed fold."""

    family: str
    label: str
    inner_validation_score: float | None
    selected: bool


@dataclass(frozen=True, slots=True)
class SelectionFoldDisplay:
    """Per-fold winner, inner scores, and train/test gap for the selection panel."""

    fold_id: int
    winner_family: str
    candidates: tuple[SelectionCandidateScore, ...]
    train_primary: float | None
    test_primary: float | None
    primary_gap: float | None


@dataclass(frozen=True, slots=True)
class PredictiveReportViewModel:
    """Presentation-ready snapshot of one Predictive Research run.

    Figure builders must consume this object only — never raw parquet reads.
    """

    run_id: str
    dataset_id: str
    generated_at_utc: datetime
    task_type: TaskType
    primary_metric: str
    has_probabilities: bool
    decision_threshold: float
    fold_timeline: tuple[FoldTimelineBand, ...]
    fold_metrics: tuple[FoldMetricSnapshot, ...]
    pooled_model: float | None
    pooled_baselines: Mapping[str, float | None]
    predictions: pl.DataFrame
    exclusion_counts: Mapping[str, int]
    role_counts: Mapping[str, int]
    calibration_bins: tuple[CalibrationBin, ...]
    brier_score: float | None
    mean_forward_return_all: float | None
    quality_warnings: tuple[PredictiveQualityWarning, ...]
    quality_rules: PredictiveReportQualityRules
    feature_importance: tuple[FeatureImportanceBar, ...]
    leaderboard_rows: tuple[LeaderboardDisplayRow, ...]
    selection_folds: tuple[SelectionFoldDisplay, ...]


def build_predictive_report_view_model(
    source: PredictiveReportSource,
    *,
    clock: Clock,
    quality_rules: PredictiveReportQualityRules | None = None,
) -> PredictiveReportViewModel:
    """Map persisted envelopes to a report view model. Read-only; no fitting."""
    run = source.run
    dataset = source.dataset
    metrics = source.metrics
    if metrics.run_id != run.manifest.run_id:
        msg = "metrics.run_id must match the run envelope"
        raise ValidationError(msg)
    if dataset.manifest.dataset_id != run.manifest.dataset_id:
        msg = "dataset_id must match the run envelope"
        raise ValidationError(msg)

    rules = quality_rules or PredictiveReportQualityRules()
    predictions = source.run.predictions
    has_probabilities = _has_probabilities(predictions)
    test_rows_by_fold = _test_rows_by_fold(predictions)
    role_counts = _role_counts(dataset.features)
    timeline = _fold_timeline(dataset.features)
    fold_metrics = _fold_metric_snapshots(metrics, test_rows_by_fold)
    test_labels = tuple(
        float(value) for value in predictions.get_column("y_true").to_list() if value is not None
    )
    warnings = evaluate_predictive_quality_flags(
        metrics=metrics,
        test_rows_by_fold=test_rows_by_fold,
        test_labels=test_labels,
        exclusion_counts={
            str(key): int(value) for key, value in dataset.manifest.exclusion_counts.items()
        },
        role_counts=role_counts,
        rules=rules,
    )
    pooled_model = primary_metric_value(
        metrics.pooled[MetricSource.MODEL.value].statistical, metrics.task_type
    )
    pooled_baselines = {
        source_name: primary_metric_value(source_metrics.statistical, metrics.task_type)
        for source_name, source_metrics in metrics.pooled.items()
        if source_name != MetricSource.MODEL.value
    }
    model_metrics = metrics.pooled[MetricSource.MODEL.value]
    generated_at = require_utc_aware(clock.now())
    return PredictiveReportViewModel(
        run_id=run.manifest.run_id,
        dataset_id=run.manifest.dataset_id,
        generated_at_utc=generated_at,
        task_type=metrics.task_type,
        primary_metric=primary_metric_name(metrics.task_type),
        has_probabilities=has_probabilities,
        decision_threshold=metrics.decision_threshold,
        fold_timeline=timeline,
        fold_metrics=fold_metrics,
        pooled_model=pooled_model,
        pooled_baselines=MappingProxyType(pooled_baselines),
        predictions=predictions,
        exclusion_counts=MappingProxyType(
            {str(key): int(value) for key, value in dataset.manifest.exclusion_counts.items()}
        ),
        role_counts=MappingProxyType(role_counts),
        calibration_bins=model_metrics.statistical.calibration_bins,
        brier_score=model_metrics.statistical.brier_score,
        mean_forward_return_all=model_metrics.finance.mean_forward_return_all,
        quality_warnings=warnings,
        quality_rules=rules,
        feature_importance=_feature_importance_bars(source.importance),
        leaderboard_rows=_leaderboard_rows(source.leaderboard),
        selection_folds=_selection_folds(source.selection, metrics.fold_primary),
    )


def _has_probabilities(predictions: pl.DataFrame) -> bool:
    if "y_proba" not in predictions.columns:
        return False
    values = predictions.get_column("y_proba").to_list()
    return any(value is not None and value == value for value in values)


def _test_rows_by_fold(predictions: pl.DataFrame) -> dict[int, int]:
    counts: dict[int, int] = {}
    for fold_id in predictions.get_column("fold_id").to_list():
        key = int(fold_id)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _role_counts(features: pl.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {role.value: 0 for role in FoldRole}
    for role in features.get_column("fold_role").to_list():
        key = str(role)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _fold_timeline(features: pl.DataFrame) -> tuple[FoldTimelineBand, ...]:
    required = {"fold_id", "fold_role", "available_at"}
    missing = required.difference(features.columns)
    if missing:
        msg = f"dataset features missing {sorted(missing)[0]}"
        raise ValidationError(msg)
    bands: list[FoldTimelineBand] = []
    fold_ids = sorted(int(value) for value in features.get_column("fold_id").unique().to_list())
    for fold_id in fold_ids:
        fold_rows = features.filter(pl.col("fold_id") == fold_id)
        for role in FoldRole:
            role_rows = fold_rows.filter(pl.col("fold_role") == role.value)
            if role_rows.height == 0:
                continue
            available = role_rows.get_column("available_at")
            bands.append(
                FoldTimelineBand(
                    fold_id=fold_id,
                    role=role.value,
                    start=available.min(),  # type: ignore[arg-type]
                    end=available.max(),  # type: ignore[arg-type]
                    row_count=role_rows.height,
                )
            )
    return tuple(bands)


def _fold_metric_snapshots(
    metrics: PredictiveMetricsReport,
    test_rows_by_fold: dict[int, int],
) -> tuple[FoldMetricSnapshot, ...]:
    snapshots: list[FoldMetricSnapshot] = []
    task_type = metrics.task_type
    for fold_key, sources in sorted(metrics.folds.items(), key=lambda item: int(item[0])):
        fold_id = int(fold_key)
        baselines = {
            source_name: primary_metric_value(source_metrics.statistical, task_type)
            for source_name, source_metrics in sources.items()
            if source_name != MetricSource.MODEL.value
        }
        snapshots.append(
            FoldMetricSnapshot(
                fold_id=fold_id,
                test_rows=test_rows_by_fold.get(fold_id, 0),
                model=primary_metric_value(
                    sources[MetricSource.MODEL.value].statistical, task_type
                ),
                baselines=MappingProxyType(baselines),
            )
        )
    return tuple(snapshots)


def _feature_importance_bars(trace: ImportanceTrace | None) -> tuple[FeatureImportanceBar, ...]:
    if trace is None or not trace.folds:
        return ()
    names: list[str] = []
    seen: set[str] = set()
    for fold in trace.folds:
        for name in fold.permutation.feature_names:
            if name not in seen:
                seen.add(name)
                names.append(name)
        if fold.native is None:
            continue
        for name in fold.native.feature_names:
            if name not in seen:
                seen.add(name)
                names.append(name)
    bars: list[FeatureImportanceBar] = []
    for name in names:
        perm_means: list[float] = []
        perm_stds: list[float] = []
        native_gains: list[float] = []
        for fold in trace.folds:
            perm_map = dict(
                zip(fold.permutation.feature_names, fold.permutation.importances_mean, strict=True)
            )
            std_map = dict(
                zip(fold.permutation.feature_names, fold.permutation.importances_std, strict=True)
            )
            if name in perm_map:
                perm_means.append(float(perm_map[name]))
                perm_stds.append(float(std_map[name]))
            if fold.native is None:
                continue
            native_map = dict(zip(fold.native.feature_names, fold.native.gain, strict=True))
            if name in native_map:
                native_gains.append(float(native_map[name]))
        bars.append(
            FeatureImportanceBar(
                feature_name=name,
                native_gain=None if not native_gains else sum(native_gains) / len(native_gains),
                permutation_mean=0.0 if not perm_means else sum(perm_means) / len(perm_means),
                permutation_std=0.0 if not perm_stds else sum(perm_stds) / len(perm_stds),
            )
        )
    return tuple(sorted(bars, key=lambda bar: bar.permutation_mean, reverse=True))


def _leaderboard_rows(
    leaderboard: PredictiveLeaderboard | None,
) -> tuple[LeaderboardDisplayRow, ...]:
    if leaderboard is None:
        return ()
    return tuple(
        LeaderboardDisplayRow(
            rank=row.rank,
            kind=row.kind.value,
            family=row.family,
            source=row.source,
            pooled_primary=row.pooled_primary,
            metric=row.metric,
            run_id=row.run_id,
        )
        for row in leaderboard.rows
    )


def _selection_folds(
    selection: SelectionTrace | None,
    fold_primary: Mapping[str, Mapping[str, float | None]] | None,
) -> tuple[SelectionFoldDisplay, ...]:
    if selection is None or not selection.folds:
        return ()
    gaps = fold_primary or {}
    family_counts: dict[str, int] = {}
    for fold in selection.folds:
        for candidate in fold.candidates:
            family_counts[candidate.family] = family_counts.get(candidate.family, 0) + 1
    displayed: list[SelectionFoldDisplay] = []
    for fold in selection.folds:
        gap = gaps.get(str(fold.fold_id), {})
        displayed.append(
            SelectionFoldDisplay(
                fold_id=fold.fold_id,
                winner_family=fold.winner.family,
                candidates=tuple(
                    SelectionCandidateScore(
                        family=candidate.family,
                        label=(
                            candidate.family
                            if family_counts[candidate.family] <= len(selection.folds)
                            else f"{candidate.family} ({candidate.identity_hash[-8:]})"
                        ),
                        inner_validation_score=candidate.inner_validation_score,
                        selected=candidate.selected,
                    )
                    for candidate in fold.candidates
                ),
                train_primary=gap.get("train_primary"),
                test_primary=gap.get("test_primary"),
                primary_gap=gap.get("primary_gap"),
            )
        )
    return tuple(displayed)
