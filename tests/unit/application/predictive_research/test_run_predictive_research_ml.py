"""ML extra tests for Predictive Research run orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    RunPredictiveResearchRequest,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_model_path
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRepository,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.datasets.predictive_run import PredictiveRunRepository
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PreprocessingSpec,
    PreprocessingStep,
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


def _labelled_rows(count: int = 40) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    returns = [0.01 + (index * 0.001) for index in range(count)]
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [float(index) for index in range(count)],
            "label": returns,
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


def test_sklearn_run_persists_test_predictions_and_joblib_blobs(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    features = assign_purged_walk_forward_folds(
        _labelled_rows(),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )
    dataset_ref = PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id="0123456789abcdef",
                study_spec={
                    "study_id": "atr_forward_return",
                    "label": {"kind": "REGRESSION", "horizon": "5m"},
                },
                definition_hash="a" * 64,
                dataset_fingerprint="0123456789abcdef" + ("b" * 48),
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
    )
    spec = EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=7,
        task_type=TaskType.REGRESSION,
    )
    first = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, tzinfo=UTC)),
        )
    )
    second = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=False,
        )
    )
    test_rows = features.filter(pl.col("fold_role") == FoldRole.TEST.value)
    predictions = first.envelope.predictions
    assert first.run_id == second.run_id
    assert predictions.height == test_rows.height
    assert (
        predictions.get_column("forward_return").to_list()
        == test_rows.get_column("forward_return").to_list()
    )
    assert all(value is None for value in predictions.get_column("y_proba").to_list())
    fold_ids = sorted({int(value) for value in predictions.get_column("fold_id").to_list()})
    for fold_id in fold_ids:
        blob = predictive_research_run_model_path(storage_root, first.run_id, fold_id)
        assert blob.exists()
        assert blob.stat().st_size > 0

    loaded = PredictiveRunRepository(storage_root).read(first.run_ref)
    assert loaded.manifest.library == "sklearn"
    assert loaded.manifest.estimator_description["library"] == "sklearn"
    assert loaded.predictions.height == predictions.height
