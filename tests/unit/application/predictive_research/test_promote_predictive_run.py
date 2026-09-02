"""ML extra tests for promoting an existing Predictive Research run (S049-T008)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    PromotePredictiveRunRequest,
    RunPredictiveResearchRequest,
    promote_predictive_run,
    run_predictive_research,
)
from trading_framework.application.predictive_research.run_predictive_research import (
    RunPredictiveResearchResult,
)
from trading_framework.infrastructure.ml.promotion import (
    PromotedFamilyUnsupportedError,
    PromotionVersionMismatchError,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_runs_root,
    promoted_artifacts_root,
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
from trading_framework.research.datasets.predictive_run import (
    PREDICTIVE_RUN_SCHEMA_VERSION,
    PredictiveRunEnvelope,
    PredictiveRunManifest,
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.predictive import (
    EstimatorSpec,
    FeatureMatrixSpec,
    FeatureSpec,
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


def _atr_feature(alias: str = "atr_14") -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias=alias,
    )


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


def _split_features() -> pl.DataFrame:
    return assign_purged_walk_forward_folds(
        _labelled_rows(),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )


def _write_regression_dataset(
    storage_root: Path,
    features: pl.DataFrame,
    *,
    dataset_id: str = "0123456789abcdef",
) -> PredictiveDatasetRef:
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "atr_forward_return",
                    "label": {"kind": "REGRESSION", "horizon": "5m"},
                    "features": FeatureMatrixSpec(features=(_atr_feature(),)).to_dict(),
                },
                definition_hash="a" * 64,
                dataset_fingerprint=dataset_id + ("b" * 48),
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


def _ridge_spec() -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _run_fixture(storage_root: Path) -> RunPredictiveResearchResult:
    features = _split_features()
    dataset_ref = _write_regression_dataset(storage_root, features)
    return run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=_ridge_spec(),
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, tzinfo=UTC)),
        )
    )


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_fake_run(
    storage_root: Path,
    features: pl.DataFrame,
    *,
    family: str,
    library_version: str,
) -> PredictiveRunRef:
    test_rows = features.filter(pl.col("fold_role") == "TEST")
    predictions = test_rows.select(
        [
            pl.col("entity_id"),
            pl.col("fold_id").cast(pl.Int64),
            pl.col("label").alias("y_true"),
            pl.col("label").alias("y_pred"),
            pl.lit(None, dtype=pl.Float64).alias("y_proba"),
            pl.col("forward_return"),
        ]
    )
    manifest = PredictiveRunManifest(
        schema_version=PREDICTIVE_RUN_SCHEMA_VERSION,
        run_id="fake0000run00001",
        run_fingerprint="f" * 64,
        dataset_id="0123456789abcdef",
        dataset_fingerprint="0123456789abcdef" + ("b" * 48),
        estimator_spec={
            "family": family,
            "hyperparameters": {},
            "seed": 7,
            "task_type": "REGRESSION",
        },
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        library="sklearn",
        library_version=library_version,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 7, 1, tzinfo=UTC),
        model_files={"0": "models/fold_0.bin", "1": "models/fold_1.bin"},
        estimator_description={"library": "sklearn", "family": family},
    )
    return PredictiveRunRepository(storage_root).write(
        PredictiveRunEnvelope(manifest=manifest, predictions=predictions),
        model_blobs={0: b"not-a-real-blob", 1: b"not-a-real-blob"},
    )


def test_promote_writes_manifest_matching_run_fingerprint_and_last_fold(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = _run_fixture(storage_root)

    result = promote_predictive_run(
        PromotePredictiveRunRequest(run_ref=run_result.run_ref, storage_root=storage_root)
    )

    assert result.directory.is_dir()
    manifest_path = result.directory / "manifest.json"
    payload_path = result.directory / "artifact.json"
    assert manifest_path.is_file()
    assert payload_path.is_file()
    assert {path.name for path in result.directory.iterdir()} == {
        "manifest.json",
        "artifact.json",
    }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_fingerprint"] == run_result.fingerprint
    assert manifest["artifact_fingerprint"] == result.artifact_fingerprint
    expected_last_fold = max(
        int(value)
        for value in run_result.envelope.predictions.get_column("fold_id").unique().to_list()
    )
    assert manifest["fold_id"] == expected_last_fold == result.fold_id


def test_promote_does_not_modify_the_source_run_directory(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = _run_fixture(storage_root)
    run_dir = predictive_research_runs_root(storage_root) / run_result.run_id
    before = _hash_tree(run_dir)

    promote_predictive_run(
        PromotePredictiveRunRequest(run_ref=run_result.run_ref, storage_root=storage_root)
    )

    after = _hash_tree(run_dir)
    assert after == before


def test_promote_refuses_unsupported_family_and_writes_nothing(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    features = _split_features()
    _write_regression_dataset(storage_root, features)
    run_ref = _write_fake_run(
        storage_root, features, family="xgboost.regressor", library_version="1.7.0"
    )

    with pytest.raises(PromotedFamilyUnsupportedError):
        promote_predictive_run(
            PromotePredictiveRunRequest(run_ref=run_ref, storage_root=storage_root)
        )

    assert not promoted_artifacts_root(storage_root).exists()


def test_promote_refuses_version_mismatch_and_writes_nothing(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    features = _split_features()
    _write_regression_dataset(storage_root, features)
    run_ref = _write_fake_run(
        storage_root,
        features,
        family="sklearn.ridge",
        library_version="0.0.0-not-installed",
    )

    with pytest.raises(PromotionVersionMismatchError):
        promote_predictive_run(
            PromotePredictiveRunRequest(run_ref=run_ref, storage_root=storage_root)
        )

    assert not promoted_artifacts_root(storage_root).exists()
