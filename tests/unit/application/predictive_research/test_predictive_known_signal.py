"""T021: known-signal fixture (SPRINT_040 §9, D-S040-13).

Synthetic labelled frames only — no NQ. Ridge must recover a real signal;
pure-noise labels must not beat the permutation baseline (leakage tripwire).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    AnalyzePredictiveRunRequest,
    RunPredictiveResearchRequest,
    analyze_predictive_run,
    run_predictive_research,
)
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.predictive import (
    EstimatorSpec,
    MetricSource,
    PredictiveMetricsReport,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_ROW_COUNT = 300
_SIGNAL_RANK_IC_FLOOR = 0.45
_SIGNAL_VS_PERMUTATION_MARGIN = 0.25
_BINARY_AUC_FLOOR = 0.65
_NOISE_SPEARMAN_BAND = 0.15
_NOISE_AUC_BAND = 0.10
_REGRESSION_FAMILIES = ("sklearn.ridge", "sklearn.elastic_net")


def _split_spec() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=4,
        test_span=Timeframe("40m"),
        embargo_span=Timeframe("5m"),
        min_train_rows=40,
    )


def _labelled_rows(
    *,
    mode: str,
    seed: int = 42,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(_ROW_COUNT)]
    signal_x = rng.normal(0.0, 1.0, _ROW_COUNT)
    noise_a = rng.normal(0.0, 1.0, _ROW_COUNT)
    noise_b = rng.normal(0.0, 1.0, _ROW_COUNT)
    residual = rng.normal(0.0, 0.25, _ROW_COUNT)
    if mode == "known_signal":
        labels = 2.0 * signal_x + residual
        returns = labels
    elif mode == "binary_signal":
        logits = 2.5 * signal_x + residual
        labels = (logits > 0.0).astype(np.float64)
        returns = logits
    elif mode == "noise":
        labels = rng.normal(0.0, 1.0, _ROW_COUNT)
        returns = rng.normal(0.0, 1.0, _ROW_COUNT)
    elif mode == "binary_noise":
        labels = rng.integers(0, 2, _ROW_COUNT).astype(np.float64)
        returns = rng.normal(0.0, 1.0, _ROW_COUNT)
    else:
        msg = f"unknown labelled-row mode: {mode}"
        raise ValueError(msg)
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * _ROW_COUNT,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "signal_x": signal_x.tolist(),
            "noise_a": noise_a.tolist(),
            "noise_b": noise_b.tolist(),
            "label": labels.tolist(),
            "forward_return": returns.tolist(),
            "outcome_status": ["COMPLETE"] * _ROW_COUNT,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC_US,
            "available_at": _UTC_US,
            "label_end_at": _UTC_US,
            "signal_x": pl.Float64(),
            "noise_a": pl.Float64(),
            "noise_b": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _shuffle_labels(rows: pl.DataFrame, *, seed: int) -> pl.DataFrame:
    shuffled = np.asarray(rows.get_column("label").to_list(), dtype=np.float64).copy()
    np.random.default_rng(seed).shuffle(shuffled)
    return rows.with_columns(pl.Series("label", shuffled, dtype=pl.Float64))


def _write_dataset(
    storage_root: Path,
    rows: pl.DataFrame,
    *,
    dataset_id: str,
    label_kind: str,
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(rows, _split_spec())
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "known_signal_fixture",
                    "label": {"kind": label_kind, "horizon": "5m"},
                },
                definition_hash="b" * 64,
                dataset_fingerprint=dataset_id + ("d" * 48),
                source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
                exclusion_counts={
                    "candidate_rows": _ROW_COUNT,
                    "labelled_rows": _ROW_COUNT,
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
    )


def _estimator(family: str, task_type: TaskType) -> EstimatorSpec:
    hyperparameters: dict[str, float]
    if family == "sklearn.elastic_net":
        hyperparameters = {"alpha": 0.1, "l1_ratio": 0.2}
    elif family == "sklearn.logistic":
        hyperparameters = {"C": 1.0}
    else:
        hyperparameters = {"alpha": 0.1}
    return EstimatorSpec(
        family=family,
        hyperparameters=hyperparameters,
        seed=7,
        task_type=task_type,
    )


def _run_and_analyze(
    storage_root: Path,
    dataset_ref: PredictiveDatasetRef,
    spec: EstimatorSpec,
) -> PredictiveMetricsReport:
    result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )
    analyzed = analyze_predictive_run(
        AnalyzePredictiveRunRequest(
            run_ref=result.run_ref,
            storage_root=storage_root,
            persist=False,
        )
    )
    assert analyzed.run_id == result.run_id
    return analyzed.report


def _metric_value(value: float | None, *, missing: float) -> float:
    if value is None:
        return missing
    return float(value)


def _statistical(
    report: PredictiveMetricsReport,
    source: str,
    field: str,
    *,
    missing: float,
) -> float:
    return _metric_value(getattr(report.pooled[source].statistical, field), missing=missing)


def _fold_statistical(
    report: PredictiveMetricsReport,
    source: str,
    field: str,
    *,
    missing: float,
) -> tuple[float, ...]:
    return tuple(
        _metric_value(getattr(sources[source].statistical, field), missing=missing)
        for sources in report.folds.values()
    )


def _assert_within_permutation_spread(
    report: PredictiveMetricsReport,
    field: str,
    *,
    band: float,
    missing: float,
) -> None:
    model_pooled = _statistical(report, MetricSource.MODEL.value, field, missing=missing)
    perm_pooled = _statistical(
        report, MetricSource.RANDOM_PERMUTATION.value, field, missing=missing
    )
    perm_folds = _fold_statistical(
        report, MetricSource.RANDOM_PERMUTATION.value, field, missing=missing
    )
    spread_low = min((*perm_folds, perm_pooled)) - band
    spread_high = max((*perm_folds, perm_pooled)) + band
    assert spread_low <= model_pooled <= spread_high
    # Leakage tripwire: a model that "finds" structure sits far above this band.


def test_ridge_recovers_known_signal_above_permutation(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="known_signal"),
        dataset_id="aaaabbbbccccdddd",
        label_kind="REGRESSION",
    )
    report = _run_and_analyze(
        storage_root,
        dataset_ref,
        _estimator("sklearn.ridge", TaskType.REGRESSION),
    )
    model_ic = _statistical(report, MetricSource.MODEL.value, "spearman_ic", missing=0.0)
    perm_ic = _statistical(
        report, MetricSource.RANDOM_PERMUTATION.value, "spearman_ic", missing=0.0
    )
    assert model_ic > _SIGNAL_RANK_IC_FLOOR
    assert model_ic > perm_ic + _SIGNAL_VS_PERMUTATION_MARGIN


def test_logistic_recovers_binary_known_signal_auc(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="binary_signal"),
        dataset_id="bbbbccccddddeeee",
        label_kind="BINARY",
    )
    report = _run_and_analyze(
        storage_root,
        dataset_ref,
        _estimator("sklearn.logistic", TaskType.CLASSIFICATION),
    )
    model_auc = _statistical(report, MetricSource.MODEL.value, "roc_auc", missing=0.5)
    perm_auc = _statistical(report, MetricSource.RANDOM_PERMUTATION.value, "roc_auc", missing=0.5)
    assert model_auc > _BINARY_AUC_FLOOR
    assert model_auc > 0.5
    assert model_auc > perm_auc + _SIGNAL_VS_PERMUTATION_MARGIN / 2


def test_pure_noise_label_stays_within_permutation_spread(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    regression_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="noise"),
        dataset_id="ccccddddeeeeffff",
        label_kind="REGRESSION",
    )
    for family in _REGRESSION_FAMILIES:
        report = _run_and_analyze(
            storage_root,
            regression_ref,
            _estimator(family, TaskType.REGRESSION),
        )
        _assert_within_permutation_spread(
            report, "spearman_ic", band=_NOISE_SPEARMAN_BAND, missing=0.0
        )

    classification_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="binary_noise"),
        dataset_id="ddddeeeeffff0000",
        label_kind="BINARY",
    )
    report = _run_and_analyze(
        storage_root,
        classification_ref,
        _estimator("sklearn.logistic", TaskType.CLASSIFICATION),
    )
    _assert_within_permutation_spread(report, "roc_auc", band=_NOISE_AUC_BAND, missing=0.5)


def test_shuffling_the_label_column_destroys_performance(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    shuffled_regression = _shuffle_labels(_labelled_rows(mode="known_signal"), seed=99)
    regression_ref = _write_dataset(
        storage_root,
        shuffled_regression,
        dataset_id="eeeeffff00001111",
        label_kind="REGRESSION",
    )
    for family in _REGRESSION_FAMILIES:
        report = _run_and_analyze(
            storage_root,
            regression_ref,
            _estimator(family, TaskType.REGRESSION),
        )
        _assert_within_permutation_spread(
            report, "spearman_ic", band=_NOISE_SPEARMAN_BAND, missing=0.0
        )
        assert (
            _statistical(report, MetricSource.MODEL.value, "spearman_ic", missing=0.0)
            < _SIGNAL_RANK_IC_FLOOR
        )

    shuffled_binary = _shuffle_labels(_labelled_rows(mode="binary_signal"), seed=99)
    classification_ref = _write_dataset(
        storage_root,
        shuffled_binary,
        dataset_id="ffff000011112222",
        label_kind="BINARY",
    )
    report = _run_and_analyze(
        storage_root,
        classification_ref,
        _estimator("sklearn.logistic", TaskType.CLASSIFICATION),
    )
    _assert_within_permutation_spread(report, "roc_auc", band=_NOISE_AUC_BAND, missing=0.5)
    assert (
        _statistical(report, MetricSource.MODEL.value, "roc_auc", missing=0.5) < _BINARY_AUC_FLOOR
    )
