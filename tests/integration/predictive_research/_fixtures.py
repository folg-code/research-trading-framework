"""Shared synthetic-run/promotion fixtures for the promoted-artifact integration suite.

Not named ``test_*`` so pytest never collects it (mirrors
``tests/unit/research/predictive/_promoted_artifact_fixtures.py``). Builds a
D-S039-CI-dataset-shaped synthetic fixture (SPRINT_039 §9 / ADR-0023 §8:
synthetic, no NQ dependency, deterministic under a fixed seed), runs
Predictive Research on it, and promotes the result -- reused by T010b
(parity), T011 (determinism + refusal) and T012 (condition coverage) so the
same fixture construction backs all three test files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

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
from trading_framework.infrastructure.storage.paths import promoted_artifact_payload_path
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
from trading_framework.research.datasets.promoted_artifact import (
    PromotedArtifactManifest,
    PromotedArtifactRef,
    PromotedArtifactRepository,
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
from trading_framework.research.predictive.promotion.parameters import (
    PromotedArtifactParameters,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")

#: D-S039-CI-dataset shape: synthetic, no NQ dependency, deterministic
#: under a fixed seed.
ROW_COUNT = 300
FEATURE_COLUMNS = ("signal_x", "noise_a")


def split_spec() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=4,
        test_span=Timeframe("40m"),
        embargo_span=Timeframe("5m"),
        min_train_rows=40,
    )


def labelled_rows(*, mode: str, seed: int = 42) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(ROW_COUNT)]
    signal_x = rng.normal(0.0, 1.0, ROW_COUNT)
    noise_a = rng.normal(0.0, 1.0, ROW_COUNT)
    residual = rng.normal(0.0, 0.25, ROW_COUNT)
    if mode == "regression":
        labels = 2.0 * signal_x + residual
        returns = labels
    elif mode == "binary":
        logits = 2.5 * signal_x + residual
        labels = (logits > 0.0).astype(np.float64)
        returns = logits
    else:
        msg = f"unknown labelled-row mode: {mode}"
        raise ValueError(msg)
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * ROW_COUNT,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "signal_x": signal_x.tolist(),
            "noise_a": noise_a.tolist(),
            "label": labels.tolist(),
            "forward_return": returns.tolist(),
            "outcome_status": ["COMPLETE"] * ROW_COUNT,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": UTC_US,
            "available_at": UTC_US,
            "label_end_at": UTC_US,
            "signal_x": pl.Float64(),
            "noise_a": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def declared_features() -> FeatureMatrixSpec:
    return FeatureMatrixSpec(
        features=(
            FeatureSpec(
                component_id=ComponentId("synthetic.signal_x"),
                parameters=CanonicalParameters.from_mapping({}),
                output_id=OutputId("value"),
                alias="signal_x",
            ),
            FeatureSpec(
                component_id=ComponentId("synthetic.noise_a"),
                parameters=CanonicalParameters.from_mapping({}),
                output_id=OutputId("value"),
                alias="noise_a",
            ),
        )
    )


def write_dataset(
    storage_root: Path,
    rows: pl.DataFrame,
    *,
    dataset_id: str,
    label_kind: str,
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(rows, split_spec())
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "promoted_artifact_fixture",
                    "label": {"kind": label_kind, "horizon": "5m"},
                    "features": declared_features().to_dict(),
                },
                definition_hash="b" * 64,
                dataset_fingerprint=dataset_id + ("d" * 48),
                source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
                exclusion_counts={
                    "candidate_rows": ROW_COUNT,
                    "labelled_rows": ROW_COUNT,
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


def estimator(family: str, task_type: TaskType) -> EstimatorSpec:
    hyperparameters: dict[str, float] = (
        {"C": 1.0} if family == "sklearn.logistic" else {"alpha": 1.0}
    )
    return EstimatorSpec(
        family=family, hyperparameters=hyperparameters, seed=7, task_type=task_type
    )


def run_fixture(
    storage_root: Path,
    *,
    mode: str,
    label_kind: str,
    family: str,
    task_type: TaskType,
    dataset_id: str,
    seed: int = 42,
) -> RunPredictiveResearchResult:
    dataset_ref = write_dataset(
        storage_root,
        labelled_rows(mode=mode, seed=seed),
        dataset_id=dataset_id,
        label_kind=label_kind,
    )
    return run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=estimator(family, task_type),
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )


def promote(storage_root: Path, run_result: RunPredictiveResearchResult) -> PromotedArtifactRef:
    """Promote ``run_result`` under a fixed clock, so ``created_at_utc`` (and
    therefore the manifest's bytes) is reproducible across independent calls
    with the same inputs -- needed for T011's byte-identical determinism
    case, not just this file's own tests.
    """
    result = promote_predictive_run(
        PromotePredictiveRunRequest(
            run_ref=run_result.run_ref,
            storage_root=storage_root,
            clock=FixedClock(datetime(2024, 7, 2, 9, 0, tzinfo=UTC)),
        )
    )
    return PromotedArtifactRef(artifact_fingerprint=result.artifact_fingerprint)


def read_promoted(
    storage_root: Path, ref: PromotedArtifactRef
) -> tuple[PromotedArtifactManifest, PromotedArtifactParameters]:
    repository = PromotedArtifactRepository(storage_root)
    manifest = repository.read_manifest(ref)
    payload_path = promoted_artifact_payload_path(storage_root, ref.artifact_fingerprint)
    payload = PromotedArtifactParameters.from_dict(
        json.loads(payload_path.read_text(encoding="utf-8"))
    )
    return manifest, payload
