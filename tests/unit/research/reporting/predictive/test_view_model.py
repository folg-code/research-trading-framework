"""Tests for Predictive Research report view model, flags, and panel registry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.datasets.predictive_run import (
    PREDICTIVE_RUN_SCHEMA_VERSION,
    PredictiveRunEnvelope,
    PredictiveRunManifest,
)
from trading_framework.research.predictive import (
    FoldRole,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    assign_purged_walk_forward_folds,
)
from trading_framework.research.predictive.estimators import (
    EstimatorSpec,
    NativeFeatureImportance,
    TaskType,
)
from trading_framework.research.predictive.importance import (
    FoldImportanceRecord,
    FoldPrimaryGap,
    ImportanceTrace,
    PermutationImportance,
)
from trading_framework.research.predictive.leaderboard import (
    LeaderboardRow,
    LeaderboardRowKind,
    PredictiveLeaderboard,
)
from trading_framework.research.predictive.metrics import (
    DECILE_COUNT,
    PREDICTIVE_METRICS_SCHEMA_VERSION,
    CalibrationBin,
    FinanceMetrics,
    MetricSource,
    PredictiveMetricsReport,
    SourceMetrics,
    StatisticalMetrics,
)
from trading_framework.research.predictive.selection import (
    CandidateFoldScore,
    FoldSelectionTrace,
    SelectionMetric,
    SelectionTrace,
)
from trading_framework.research.reporting.predictive import (
    PREDICTIVE_REPORT_PANELS,
    RESERVED_PANEL_IDS,
    PanelStatus,
    PredictiveQualityFlag,
    PredictiveReportQualityRules,
    PredictiveReportSource,
    build_predictive_report_view_model,
    resolve_report_panels,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_GENERATED = datetime(2024, 8, 1, 12, 0, tzinfo=UTC)


def _empty_finance() -> FinanceMetrics:
    return FinanceMetrics(
        mean_forward_return_by_decile=tuple([None] * DECILE_COUNT),
        top_bottom_spread=None,
        hit_rate=None,
        coverage=0.0,
        mean_forward_return_selected=None,
        mean_forward_return_all=0.01,
    )


def _source(*, spearman: float | None = None, roc_auc: float | None = None) -> SourceMetrics:
    return SourceMetrics(
        statistical=StatisticalMetrics(spearman_ic=spearman, roc_auc=roc_auc),
        finance=_empty_finance(),
    )


def _labelled_rows(count: int = 40, *, binary: bool = False) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    returns = [0.01 + (index * 0.001) for index in range(count)]
    labels = [1.0 if index % 2 else 0.0 for index in range(count)] if binary else returns
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [1.0] * count,
            "label": labels,
            "forward_return": returns,
            "outcome_status": ["COMPLETE"] * count,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC_US,
            "available_at": _UTC_US,
            "label_end_at": _UTC_US,
            "atr_14": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _dataset(*, binary: bool = False) -> PredictiveDatasetEnvelope:
    features = assign_purged_walk_forward_folds(
        _labelled_rows(binary=binary),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )
    return PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id="0123456789abcdef",
            study_spec={"study_id": "report_fixture"},
            definition_hash="a" * 64,
            dataset_fingerprint="b" * 64,
            source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
            exclusion_counts={
                "candidate_rows": 40,
                "labelled_rows": 40,
                "incomplete_horizon": 0,
                "insufficient_data": 0,
                "null_features": 0,
            },
            fold_summary=fold_summary_from_features(features),
            framework_version=framework_version,
            created_at_utc=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        ),
        features=features,
        folds=resolve_fold_boundaries(features),
    )


def _predictions_from_dataset(
    dataset: PredictiveDatasetEnvelope, *, with_proba: bool
) -> pl.DataFrame:
    test = dataset.features.filter(pl.col("fold_role") == FoldRole.TEST.value)
    n_rows = test.height
    proba = [0.8] * n_rows if with_proba else [None] * n_rows
    return pl.DataFrame(
        {
            "entity_id": test.get_column("entity_id").to_list(),
            "fold_id": test.get_column("fold_id").to_list(),
            "y_true": test.get_column("label").to_list(),
            "y_pred": test.get_column("label").to_list(),
            "y_proba": proba,
            "forward_return": test.get_column("forward_return").to_list(),
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


def _run(dataset: PredictiveDatasetEnvelope, predictions: pl.DataFrame) -> PredictiveRunEnvelope:
    return PredictiveRunEnvelope(
        manifest=PredictiveRunManifest(
            schema_version=PREDICTIVE_RUN_SCHEMA_VERSION,
            run_id="0123456789abcdef",
            run_fingerprint="c" * 64,
            dataset_id=dataset.manifest.dataset_id,
            dataset_fingerprint=dataset.manifest.dataset_fingerprint,
            estimator_spec={
                "family": "sklearn.ridge",
                "hyperparameters": {},
                "seed": 7,
                "task_type": "REGRESSION",
            },
            preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
            library="sklearn",
            library_version="1.6.0",
            framework_version=framework_version,
            created_at_utc=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            model_files={},
            estimator_description={"library": "sklearn", "version": "1.6.0"},
        ),
        predictions=predictions,
    )


def _metrics(
    predictions: pl.DataFrame,
    *,
    task_type: TaskType,
    model_fold_values: tuple[float, float],
    permutation_pooled: float,
    fold_primary: dict[str, dict[str, float | None]] | None = None,
) -> PredictiveMetricsReport:
    fold_ids = sorted({int(value) for value in predictions.get_column("fold_id").to_list()})
    baseline = (
        MetricSource.CONSTANT_MEAN
        if task_type is TaskType.REGRESSION
        else MetricSource.MAJORITY_CLASS
    )
    folds: dict[str, dict[str, SourceMetrics]] = {}
    for fold_id, value in zip(fold_ids, model_fold_values, strict=True):
        kwargs = {"spearman": value} if task_type is TaskType.REGRESSION else {"roc_auc": value}
        perm_kwargs = (
            {"spearman": permutation_pooled}
            if task_type is TaskType.REGRESSION
            else {"roc_auc": permutation_pooled}
        )
        folds[str(fold_id)] = {
            MetricSource.MODEL.value: _source(**kwargs),
            baseline.value: _source(**perm_kwargs),
            MetricSource.RANDOM_PERMUTATION.value: _source(**perm_kwargs),
        }
    pooled_model = sum(model_fold_values) / len(model_fold_values)
    pooled_kwargs = (
        {"spearman": pooled_model}
        if task_type is TaskType.REGRESSION
        else {"roc_auc": pooled_model}
    )
    perm_pooled = (
        {"spearman": permutation_pooled}
        if task_type is TaskType.REGRESSION
        else {"roc_auc": permutation_pooled}
    )
    return PredictiveMetricsReport(
        schema_version=PREDICTIVE_METRICS_SCHEMA_VERSION,
        run_id="0123456789abcdef",
        task_type=task_type,
        decision_threshold=0.0 if task_type is TaskType.REGRESSION else 0.5,
        seed=7,
        folds=folds,
        pooled={
            MetricSource.MODEL.value: _source(**pooled_kwargs),
            baseline.value: _source(**perm_pooled),
            MetricSource.RANDOM_PERMUTATION.value: _source(**perm_pooled),
        },
        fold_primary=fold_primary,
    )


def _source_report(
    *,
    binary: bool = False,
    with_proba: bool = False,
    model_fold_values: tuple[float, float] = (0.4, 0.5),
    permutation_pooled: float = 0.05,
    importance: ImportanceTrace | None = None,
    selection: SelectionTrace | None = None,
    leaderboard: PredictiveLeaderboard | None = None,
    fold_primary: dict[str, dict[str, float | None]] | None = None,
) -> PredictiveReportSource:
    dataset = _dataset(binary=binary)
    predictions = _predictions_from_dataset(dataset, with_proba=with_proba)
    task_type = TaskType.CLASSIFICATION if binary else TaskType.REGRESSION
    return PredictiveReportSource(
        run=_run(dataset, predictions),
        dataset=dataset,
        metrics=_metrics(
            predictions,
            task_type=task_type,
            model_fold_values=model_fold_values,
            permutation_pooled=permutation_pooled,
            fold_primary=fold_primary,
        ),
        importance=importance,
        selection=selection,
        leaderboard=leaderboard,
    )


def _permutation(*, signal: float, noise: float = 0.0) -> PermutationImportance:
    return PermutationImportance(
        feature_names=("signal", "noise"),
        importances_mean=(signal, noise),
        importances_std=(0.01, 0.01),
        n_repeats=5,
        seed=7,
        metric="spearman_ic",
    )


def _importance_trace(*, native: bool) -> ImportanceTrace:
    native_scores = (
        NativeFeatureImportance(feature_names=("signal", "noise"), gain=(2.0, 0.1))
        if native
        else None
    )
    return ImportanceTrace(
        metric="spearman_ic",
        n_repeats=5,
        folds=(
            FoldImportanceRecord(
                fold_id=0,
                native=native_scores,
                permutation=_permutation(signal=0.4),
                primary_gap=FoldPrimaryGap(train_primary=0.9, test_primary=0.4, primary_gap=0.5),
            ),
            FoldImportanceRecord(
                fold_id=1,
                native=native_scores,
                permutation=_permutation(signal=0.6),
                primary_gap=FoldPrimaryGap(train_primary=0.8, test_primary=0.5, primary_gap=0.3),
            ),
        ),
    )


def _selection_trace() -> SelectionTrace:
    winner = EstimatorSpec(
        family="xgboost.regressor",
        hyperparameters={"n_estimators": 8},
        seed=7,
        task_type=TaskType.REGRESSION,
    )
    ridge = EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=7,
        task_type=TaskType.REGRESSION,
    )
    return SelectionTrace(
        selection_metric=SelectionMetric.SPEARMAN_IC,
        inner_validation_fraction=0.2,
        folds=(
            FoldSelectionTrace(
                fold_id=0,
                winner=winner,
                candidates=(
                    CandidateFoldScore(
                        family=winner.family,
                        hyperparameters=winner.hyperparameters,
                        seed=winner.seed,
                        identity_hash="xgb",
                        inner_validation_score=0.7,
                        selected=True,
                    ),
                    CandidateFoldScore(
                        family=ridge.family,
                        hyperparameters=ridge.hyperparameters,
                        seed=ridge.seed,
                        identity_hash="ridge",
                        inner_validation_score=0.2,
                        selected=False,
                    ),
                ),
            ),
        ),
    )


def _leaderboard() -> PredictiveLeaderboard:
    return PredictiveLeaderboard(
        dataset_fingerprint="b" * 64,
        metric="spearman_ic",
        task_type=TaskType.REGRESSION,
        rows=(
            LeaderboardRow(
                rank=1,
                kind=LeaderboardRowKind.ESTIMATOR,
                run_id="xgb",
                family="xgboost.regressor",
                source="MODEL",
                pooled_primary=0.8,
                metric="spearman_ic",
                library="xgboost",
                library_version="2.1.0",
            ),
            LeaderboardRow(
                rank=2,
                kind=LeaderboardRowKind.ESTIMATOR,
                run_id="ridge",
                family="sklearn.ridge",
                source="MODEL",
                pooled_primary=0.2,
                metric="spearman_ic",
                library="sklearn",
                library_version="1.6.0",
            ),
            LeaderboardRow(
                rank=3,
                kind=LeaderboardRowKind.BASELINE,
                run_id="ridge",
                family="CONSTANT_MEAN",
                source="CONSTANT_MEAN",
                pooled_primary=0.0,
                metric="spearman_ic",
                library="sklearn",
                library_version="1.6.0",
            ),
        ),
    )


def test_view_model_is_read_only_snapshot_of_persisted_envelopes() -> None:
    source = _source_report()
    view = build_predictive_report_view_model(source, clock=FixedClock(_GENERATED))

    assert view.run_id == "0123456789abcdef"
    assert view.dataset_id == source.dataset.manifest.dataset_id
    assert view.generated_at_utc == _GENERATED
    assert view.task_type is TaskType.REGRESSION
    assert view.primary_metric == "spearman_ic"
    assert view.has_probabilities is False
    assert view.predictions.height == source.run.predictions.height
    roles = {band.role for band in view.fold_timeline}
    assert roles == {role.value for role in FoldRole}
    assert all(band.row_count > 0 for band in view.fold_timeline)
    assert len(view.fold_metrics) == 2
    assert view.pooled_model == pytest.approx(0.45)
    assert view.calibration_bins == ()
    assert view.brier_score is None
    assert view.mean_forward_return_all == pytest.approx(0.01)


def test_quality_flags_surface_threshold_and_observed_values() -> None:
    source = _source_report(model_fold_values=(0.8, 0.2), permutation_pooled=0.50)
    view = build_predictive_report_view_model(
        source,
        clock=FixedClock(_GENERATED),
        quality_rules=PredictiveReportQualityRules(
            min_test_rows=1_000,
            max_fold_metric_spread=0.10,
        ),
    )
    codes = {warning.code for warning in view.quality_warnings}
    assert PredictiveQualityFlag.SMALL_TEST_SAMPLE in codes
    assert PredictiveQualityFlag.UNSTABLE_ACROSS_FOLDS in codes
    assert PredictiveQualityFlag.WITHIN_PERMUTATION_SPREAD in codes
    permutation = next(
        warning
        for warning in view.quality_warnings
        if warning.code is PredictiveQualityFlag.WITHIN_PERMUTATION_SPREAD
    )
    assert permutation.threshold == pytest.approx(0.50)
    assert permutation.observed == pytest.approx(0.50)


def test_panel_registry_skips_calibration_without_probabilities() -> None:
    source = _source_report(binary=True, with_proba=False, model_fold_values=(0.7, 0.8))
    view = build_predictive_report_view_model(source, clock=FixedClock(_GENERATED))
    resolved = {panel.panel_id: panel for panel in resolve_report_panels(view)}

    assert view.has_probabilities is False
    assert view.task_type is TaskType.CLASSIFICATION
    assert resolved["calibration"].status is PanelStatus.SKIP
    assert resolved["calibration"].skip_reason is not None
    assert "probabilities" in resolved["calibration"].skip_reason
    assert resolved["discrimination"].status is PanelStatus.RENDER
    assert resolved["prediction_quality"].status is PanelStatus.SKIP
    assert resolved["fold_timeline"].status is PanelStatus.RENDER
    assert resolved["quality_flags"].intro
    assert resolved["feature_importance"].status is PanelStatus.SKIP
    assert resolved["leaderboard"].status is PanelStatus.SKIP
    assert resolved["selection_trace"].status is PanelStatus.SKIP
    assert resolved["feature_importance"].skip_reason is not None
    assert "importance.json" in resolved["feature_importance"].skip_reason
    assert frozenset({"learning_curves"}) == RESERVED_PANEL_IDS
    assert [definition.panel_id for definition in PREDICTIVE_REPORT_PANELS] == [
        "fold_timeline",
        "metric_stability",
        "model_vs_baselines",
        "prediction_quality",
        "discrimination",
        "calibration",
        "prediction_buckets",
        "sample_composition",
        "quality_flags",
        "feature_importance",
        "leaderboard",
        "selection_trace",
    ]


def test_classification_with_probabilities_renders_calibration() -> None:
    source = _source_report(binary=True, with_proba=True, model_fold_values=(0.7, 0.8))
    view = build_predictive_report_view_model(source, clock=FixedClock(_GENERATED))
    resolved = {panel.panel_id: panel for panel in resolve_report_panels(view)}
    assert view.has_probabilities is True
    assert resolved["calibration"].status is PanelStatus.RENDER
    assert resolved["calibration"].skip_reason is None


def test_poor_calibration_flag_uses_declared_threshold() -> None:
    source = _source_report(binary=True, with_proba=True, model_fold_values=(0.7, 0.8))
    bins = tuple(
        CalibrationBin(
            bin_index=index,
            lower=index / 10,
            upper=(index + 1) / 10,
            count=5,
            mean_predicted=0.9,
            mean_observed=0.1,
        )
        for index in range(10)
    )
    pooled = source.metrics.pooled[MetricSource.MODEL.value]
    broken = SourceMetrics(
        statistical=StatisticalMetrics(roc_auc=0.75, calibration_bins=bins),
        finance=pooled.finance,
    )
    folds = {
        fold_id: {**sources, MetricSource.MODEL.value: broken}
        for fold_id, sources in source.metrics.folds.items()
    }
    metrics = PredictiveMetricsReport(
        schema_version=source.metrics.schema_version,
        run_id=source.metrics.run_id,
        task_type=TaskType.CLASSIFICATION,
        decision_threshold=0.5,
        seed=7,
        folds=folds,
        pooled={**dict(source.metrics.pooled), MetricSource.MODEL.value: broken},
    )
    view = build_predictive_report_view_model(
        PredictiveReportSource(run=source.run, dataset=source.dataset, metrics=metrics),
        clock=FixedClock(_GENERATED),
        quality_rules=PredictiveReportQualityRules(min_test_rows=1),
    )
    codes = {warning.code for warning in view.quality_warnings}
    assert PredictiveQualityFlag.POOR_CALIBRATION in codes
    assert len(view.calibration_bins) == 10


def test_tree_sidecars_register_importance_leaderboard_and_selection_panels() -> None:
    source = _source_report(
        importance=_importance_trace(native=True),
        selection=_selection_trace(),
        leaderboard=_leaderboard(),
        fold_primary={
            "0": {"train_primary": 0.9, "test_primary": 0.4, "primary_gap": 0.5},
        },
    )
    view = build_predictive_report_view_model(source, clock=FixedClock(_GENERATED))
    resolved = {panel.panel_id: panel for panel in resolve_report_panels(view)}
    assert resolved["feature_importance"].status is PanelStatus.RENDER
    assert resolved["leaderboard"].status is PanelStatus.RENDER
    assert resolved["selection_trace"].status is PanelStatus.RENDER
    assert view.feature_importance[0].feature_name == "signal"
    assert view.feature_importance[0].native_gain == pytest.approx(2.0)
    assert view.feature_importance[0].permutation_mean == pytest.approx(0.5)
    assert [row.family for row in view.leaderboard_rows[:2]] == [
        "xgboost.regressor",
        "sklearn.ridge",
    ]
    assert view.selection_folds[0].winner_family == "xgboost.regressor"
    assert view.selection_folds[0].primary_gap == pytest.approx(0.5)


def test_large_train_test_gap_flag_uses_declared_threshold() -> None:
    source = _source_report(
        fold_primary={
            "0": {"train_primary": 0.9, "test_primary": 0.4, "primary_gap": 0.5},
            "1": {"train_primary": 0.5, "test_primary": 0.45, "primary_gap": 0.05},
        }
    )
    view = build_predictive_report_view_model(
        source,
        clock=FixedClock(_GENERATED),
        quality_rules=PredictiveReportQualityRules(min_test_rows=1),
    )
    gaps = [
        warning
        for warning in view.quality_warnings
        if warning.code is PredictiveQualityFlag.LARGE_TRAIN_TEST_GAP
    ]
    assert len(gaps) == 1
    assert gaps[0].fold_id == 0
    assert gaps[0].threshold == pytest.approx(0.20)
    assert gaps[0].observed == pytest.approx(0.5)


def test_sklearn_importance_sidecar_omits_native_gain() -> None:
    view = build_predictive_report_view_model(
        _source_report(importance=_importance_trace(native=False)),
        clock=FixedClock(_GENERATED),
    )
    assert view.feature_importance
    assert all(bar.native_gain is None for bar in view.feature_importance)
    assert view.feature_importance[0].permutation_mean == pytest.approx(0.5)
