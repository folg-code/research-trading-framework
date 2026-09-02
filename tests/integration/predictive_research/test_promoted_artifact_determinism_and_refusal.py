"""Determinism + refusal suite (S049-T011).

Six named cases, each asserting a specific error type and message content
(never a bare ``pytest.raises(Exception)``), and each docstring naming the
ADR-0024 condition it is evidence for:

    (a) promoting the same run twice is byte-identical (manifest, payload,
        fingerprint)                                             -- Condition 1
    (b) an unknown format_version refuses to load                -- Condition 1
    (c) a permuted feature order changes the fingerprint          -- Condition 1
    (d) a tree/neural family is refused at promotion, writes nothing -- Condition 5
    (e) a promotion-time version mismatch is refused, writes nothing -- Condition 5
    (f) read_manifest never reads the payload                     -- Condition 5

Condition 1 (ADR-0024 §1, "Training artifact identity") requires the
fingerprint to be present, immutable, and reproducible from the same declared
inputs -- (a), (b) and (c) are three different ways of exercising that: the
same inputs always produce the same identity, a structurally different
artifact is never silently accepted as if it were the declared one, and a
change to a hashed input (feature order) is never invisible.

Condition 5 (ADR-0024 §5, "Model registry") requires the store to be a plain
content-addressed directory with no registry, lifecycle field, or index --
(d), (e) and (f) are three different ways of exercising that a refusal never
leaves a partial/inconsistent entry behind for something registry-like to
have to reconcile, and that reading identity (the manifest) never depends on
the payload being valid, present, or even consulted.

(d) and (e) need a run whose declared ``model_family`` / ``library_version``
are deliberately wrong -- a genuinely fitted run (``run_fixture()``) cannot
produce that, so this file also builds a "fake run" fixture directly
(mirroring ``tests/unit/application/predictive_research/test_promote_predictive_run.py``).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from tests.integration.predictive_research._fixtures import (
    promote,
    read_promoted,
    run_fixture,
)
from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    PromotePredictiveRunRequest,
    promote_predictive_run,
)
from trading_framework.infrastructure.ml.promotion import (
    PromotedFamilyUnsupportedError,
    PromotionVersionMismatchError,
)
from trading_framework.infrastructure.storage.paths import (
    promoted_artifact_dir,
    promoted_artifact_manifest_path,
    promoted_artifact_payload_path,
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
from trading_framework.research.datasets.promoted_artifact import (
    PromotedArtifactRepository,
    compute_promoted_artifact_fingerprint,
)
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.research.predictive.errors import PromotedArtifactFormatError
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")


# --------------------------------------------------------------------------
# (a) Promoting the same run twice is byte-identical -- Condition 1.
# --------------------------------------------------------------------------


def test_promoting_the_same_run_twice_is_byte_identical(tmp_path: Path) -> None:
    """A JSON parameter file MUST be byte-reproducible (ADR-0024 §1).

    Two independent storage roots each get the *same* deterministic fixture
    (same seed, same estimator spec) run and promoted separately. A
    blob-based plan could only promise "loads to the same values"; a plain
    JSON parameter file can promise the much stronger "identical bytes."
    """
    manifest_bytes: list[bytes] = []
    payload_bytes: list[bytes] = []
    fingerprints: list[str] = []

    for slot in ("a", "b"):
        storage_root = tmp_path / slot
        run_result = run_fixture(
            storage_root,
            mode="regression",
            label_kind="REGRESSION",
            family="sklearn.ridge",
            task_type=TaskType.REGRESSION,
            dataset_id="1111222233334441",
            seed=42,
        )
        artifact_ref = promote(storage_root, run_result)
        fingerprints.append(artifact_ref.artifact_fingerprint)
        manifest_bytes.append(
            promoted_artifact_manifest_path(
                storage_root, artifact_ref.artifact_fingerprint
            ).read_bytes()
        )
        payload_bytes.append(
            promoted_artifact_payload_path(
                storage_root, artifact_ref.artifact_fingerprint
            ).read_bytes()
        )

    assert fingerprints[0] == fingerprints[1]
    assert manifest_bytes[0] == manifest_bytes[1]
    assert payload_bytes[0] == payload_bytes[1]


# --------------------------------------------------------------------------
# (b) An unknown format_version refuses to load -- Condition 1.
# --------------------------------------------------------------------------


def test_unknown_format_version_refuses_to_load(tmp_path: Path) -> None:
    """A structurally different artifact is never silently accepted as the
    declared one (ADR-0024 §1's identity guarantee; ADR-0029 §5's guard).
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="2222333344445551",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)

    corrupted_manifest = replace(manifest, format_version="v99")

    with pytest.raises(PromotedArtifactFormatError, match="v99") as excinfo:
        load_promoted_artifact(corrupted_manifest, payload)
    assert artifact_ref.artifact_fingerprint in str(excinfo.value)


# --------------------------------------------------------------------------
# (c) A permuted feature order changes the fingerprint -- Condition 1.
# --------------------------------------------------------------------------


def test_permuted_feature_order_changes_the_fingerprint(tmp_path: Path) -> None:
    """Feature order is part of declared identity, not incidental metadata.

    The evaluator's column order is positional (ADR-0029 §1), so a
    permutation is a genuinely different artifact -- Condition 1 requires
    the fingerprint to change, never silently accept the permutation as
    "the same" artifact.
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="3333444455556661",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, _ = read_promoted(storage_root, artifact_ref)
    assert len(manifest.feature_output_refs) >= 2

    permuted_features = tuple(reversed(manifest.feature_output_refs))
    assert permuted_features != manifest.feature_output_refs

    permuted_fingerprint = compute_promoted_artifact_fingerprint(
        run_fingerprint=manifest.run_fingerprint,
        fold_id=manifest.fold_id,
        format=manifest.format,
        format_version=manifest.format_version,
        model_family=manifest.model_family,
        features=permuted_features,
        preprocessing_spec=manifest.preprocessing_spec,
        estimator_spec=manifest.estimator_spec,
    )
    assert permuted_fingerprint != manifest.artifact_fingerprint


# --------------------------------------------------------------------------
# (d) A tree/neural family is refused at promotion, writes nothing -- Condition 5.
# --------------------------------------------------------------------------


def test_tree_family_refused_at_promotion_writes_nothing(tmp_path: Path) -> None:
    """A refused promotion never leaves a partial artifact for a registry to
    have to reconcile (ADR-0024 §5: no registry is required or implied,
    which only holds if the store never accumulates inconsistent entries).
    """
    storage_root = tmp_path / "workspace"
    features = _split_features_for_fake_run()
    _write_regression_dataset(storage_root, features)
    run_ref = _write_fake_run(
        storage_root, features, family="xgboost.regressor", library_version="1.7.0"
    )

    with pytest.raises(PromotedFamilyUnsupportedError, match=r"xgboost\.regressor"):
        promote_predictive_run(
            PromotePredictiveRunRequest(run_ref=run_ref, storage_root=storage_root)
        )

    assert not promoted_artifacts_root(storage_root).exists()


# --------------------------------------------------------------------------
# (e) A promotion-time version mismatch is refused, writes nothing -- Condition 5.
# --------------------------------------------------------------------------


def test_version_mismatch_refused_at_promotion_writes_nothing(tmp_path: Path) -> None:
    """Same guarantee as (d): the store stays empty on refusal, never partial."""
    storage_root = tmp_path / "workspace"
    features = _split_features_for_fake_run()
    _write_regression_dataset(storage_root, features)
    run_ref = _write_fake_run(
        storage_root,
        features,
        family="sklearn.ridge",
        library_version="0.0.0-not-installed",
    )

    with pytest.raises(PromotionVersionMismatchError, match=r"0\.0\.0-not-installed"):
        promote_predictive_run(
            PromotePredictiveRunRequest(run_ref=run_ref, storage_root=storage_root)
        )

    assert not promoted_artifacts_root(storage_root).exists()


# --------------------------------------------------------------------------
# (f) read_manifest never reads the payload -- Condition 5.
# --------------------------------------------------------------------------


def test_read_manifest_never_reads_the_payload(tmp_path: Path) -> None:
    """The store is a plain two-file directory, not a registry with an
    index that must always be internally consistent (ADR-0024 §5):
    identity (the manifest) is independently readable even when the payload
    is missing entirely, not merely corrupt.
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="4444555566667771",
    )
    artifact_ref = promote(storage_root, run_result)

    artifact_dir = promoted_artifact_dir(storage_root, artifact_ref.artifact_fingerprint)
    (artifact_dir / "artifact.json").unlink()
    assert not (artifact_dir / "artifact.json").exists()

    manifest = PromotedArtifactRepository(storage_root).read_manifest(artifact_ref)
    assert manifest.artifact_fingerprint == artifact_ref.artifact_fingerprint


# --------------------------------------------------------------------------
# "Fake run" fixture for (d) and (e) -- a run with a deliberately wrong
# family / library_version, which a genuinely fitted run cannot produce.
# --------------------------------------------------------------------------


def _atr_feature() -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias="atr_14",
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


def _split_features_for_fake_run() -> pl.DataFrame:
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
        run_id="fake0000run00002",
        run_fingerprint="e" * 64,
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
