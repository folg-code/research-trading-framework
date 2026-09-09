"""Tests for the threshold-sensitivity application wrapper (Sprint 058 T002)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    AnalyzeThresholdSensitivityRequest,
    RunPredictiveResearchRequest,
    ThresholdSensitivityError,
    analyze_threshold_sensitivity,
    run_predictive_research,
)
from trading_framework.application.predictive_research.run_predictive_research import (
    RunPredictiveResearchResult,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_threshold_sensitivity_path,
)
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
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
    DEFAULT_THRESHOLD_GRID,
    EstimatorSpec,
    FeatureMatrixSpec,
    FeatureSpec,
    PreprocessingSpec,
    PreprocessingStep,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    ThresholdSensitivityReport,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_ROW_COUNT = 200
UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")


def _split_spec() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=3,
        test_span=Timeframe("30m"),
        embargo_span=Timeframe("5m"),
        min_train_rows=30,
    )


def _labelled_rows(*, mode: str, seed: int = 5) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2024, 3, 1, 9, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(_ROW_COUNT)]
    signal_x = rng.normal(0.0, 1.0, _ROW_COUNT)
    residual = rng.normal(0.0, 0.3, _ROW_COUNT)
    if mode == "binary":
        logits = 2.0 * signal_x + residual
        labels = (logits > 0.0).astype(np.float64)
        returns = logits
    elif mode == "regression":
        labels = 2.0 * signal_x + residual
        returns = labels
    else:
        msg = f"unknown mode: {mode}"
        raise ValueError(msg)
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * _ROW_COUNT,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "signal_x": signal_x.tolist(),
            "label": labels.tolist(),
            "forward_return": returns.tolist(),
            "outcome_status": ["COMPLETE"] * _ROW_COUNT,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": UTC_US,
            "available_at": UTC_US,
            "label_end_at": UTC_US,
            "signal_x": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _declared_features() -> FeatureMatrixSpec:
    return FeatureMatrixSpec(
        features=(
            FeatureSpec(
                component_id=ComponentId("synthetic.signal_x"),
                parameters=CanonicalParameters.from_mapping({}),
                output_id=OutputId("value"),
                alias="signal_x",
            ),
        )
    )


def _write_dataset(
    storage_root: Path, rows: pl.DataFrame, *, dataset_id: str, label_kind: str
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(rows, _split_spec())
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "threshold_sensitivity_fixture",
                    "label": {"kind": label_kind, "horizon": "5m"},
                    "features": _declared_features().to_dict(),
                },
                definition_hash="c" * 64,
                dataset_fingerprint=dataset_id + ("e" * 48),
                source_dataset_ref="ES.c.0|ohlcv|1m|csv|threshold-sensitivity-fixture@1",
                time_range_start=datetime(2024, 3, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 3, 2, tzinfo=UTC),
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


def _run(
    storage_root: Path,
    *,
    mode: str,
    label_kind: str,
    family: str,
    task_type: TaskType,
    dataset_id: str,
) -> RunPredictiveResearchResult:
    dataset_ref = _write_dataset(
        storage_root, _labelled_rows(mode=mode), dataset_id=dataset_id, label_kind=label_kind
    )
    hyperparameters = {"C": 1.0} if family == "sklearn.logistic" else {"alpha": 1.0}
    return run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=EstimatorSpec(
                family=family, hyperparameters=hyperparameters, seed=3, task_type=task_type
            ),
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 6, 1, 13, 0, tzinfo=UTC)),
        )
    )


def test_threshold_sensitivity_sweeps_a_classification_run(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = _run(
        storage_root,
        mode="binary",
        label_kind="BINARY",
        family="sklearn.logistic",
        task_type=TaskType.CLASSIFICATION,
        dataset_id="binary_fixture",
    )

    result = analyze_threshold_sensitivity(
        AnalyzeThresholdSensitivityRequest(run_ref=run_result.run_ref, storage_root=storage_root)
    )

    assert result.run_id == run_result.run_id
    assert len(result.report.points) == len(DEFAULT_THRESHOLD_GRID)
    assert result.output_path == predictive_research_run_threshold_sensitivity_path(
        storage_root, run_result.run_id
    )
    assert result.output_path is not None
    persisted = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert ThresholdSensitivityReport.from_dict(persisted) == result.report


def test_threshold_sensitivity_refuses_a_regression_run(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = _run(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="regression_fixture",
    )

    with pytest.raises(ThresholdSensitivityError, match="requires a CLASSIFICATION run"):
        analyze_threshold_sensitivity(
            AnalyzeThresholdSensitivityRequest(
                run_ref=run_result.run_ref, storage_root=storage_root
            )
        )


def test_threshold_sensitivity_can_skip_persistence(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = _run(
        storage_root,
        mode="binary",
        label_kind="BINARY",
        family="sklearn.logistic",
        task_type=TaskType.CLASSIFICATION,
        dataset_id="binary_fixture_no_persist",
    )

    result = analyze_threshold_sensitivity(
        AnalyzeThresholdSensitivityRequest(
            run_ref=run_result.run_ref, storage_root=storage_root, persist=False
        )
    )

    assert result.output_path is None
    assert not predictive_research_run_threshold_sensitivity_path(
        storage_root, run_result.run_id
    ).exists()
