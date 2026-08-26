"""Tests for Predictive Research dataset repository round-trip."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import predictive_research_dataset_dir
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
    derive_dataset_id,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.predictive import (
    FoldRole,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.models.timeframe import Timeframe

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")


def _labelled_rows(count: int = 40) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [1.0] * count,
            "label": [0.01] * count,
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
            "outcome_status": pl.String(),
        },
    )


def _assigned_features() -> pl.DataFrame:
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


def _envelope(*, dataset_id: str = "0123456789abcdef") -> PredictiveDatasetEnvelope:
    features = _assigned_features()
    created_at = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    return PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id=dataset_id,
            study_spec={"study_id": "atr_forward_return"},
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
            created_at_utc=created_at,
        ),
        features=features,
        folds=resolve_fold_boundaries(features),
    )


def test_repository_write_read_round_trips_fold_roles_and_labels(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    envelope = _envelope()

    ref = repository.write(envelope)
    loaded = repository.read(ref)
    dataset_dir = predictive_research_dataset_dir(storage_root, envelope.manifest.dataset_id)

    assert ref == PredictiveDatasetRef(dataset_id=envelope.manifest.dataset_id)
    assert dataset_dir == (
        storage_root
        / "research"
        / "predictive_research"
        / "datasets"
        / envelope.manifest.dataset_id
    )
    assert (dataset_dir / "manifest.json").exists()
    assert (dataset_dir / "features.parquet").exists()
    assert (dataset_dir / "folds.json").exists()
    assert loaded.manifest.dataset_id == envelope.manifest.dataset_id
    assert loaded.manifest.dataset_fingerprint == envelope.manifest.dataset_fingerprint
    assert loaded.manifest.exclusion_counts == envelope.manifest.exclusion_counts
    assert loaded.manifest.fold_summary == envelope.manifest.fold_summary
    assert loaded.manifest.created_at_utc == envelope.manifest.created_at_utc
    assert loaded.folds == envelope.folds
    assert_frame_equal(loaded.features, envelope.features, check_column_order=True)
    persisted_roles = set(loaded.features.get_column("fold_role").to_list())
    assert persisted_roles <= {
        FoldRole.TRAIN.value,
        FoldRole.TEST.value,
        FoldRole.PURGED.value,
        FoldRole.EMBARGOED.value,
    }
    assert FoldRole.TRAIN.value in persisted_roles
    assert FoldRole.TEST.value in persisted_roles
    assert FoldRole.PURGED.value in persisted_roles
    assert FoldRole.EMBARGOED.value in persisted_roles
    assert (
        loaded.features.get_column("label").to_list()
        == envelope.features.get_column("label").to_list()
    )


def test_repository_refuses_overwrite(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    envelope = _envelope()
    repository.write(envelope)

    with pytest.raises(FileExistsError):
        repository.write(envelope)


def test_repository_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    envelope = _envelope()
    bad_manifest = PredictiveDatasetManifest(
        schema_version="predictive_dataset.v0",
        dataset_id=envelope.manifest.dataset_id,
        study_spec=envelope.manifest.study_spec,
        definition_hash=envelope.manifest.definition_hash,
        dataset_fingerprint=envelope.manifest.dataset_fingerprint,
        source_dataset_ref=envelope.manifest.source_dataset_ref,
        time_range_start=envelope.manifest.time_range_start,
        time_range_end=envelope.manifest.time_range_end,
        exclusion_counts=envelope.manifest.exclusion_counts,
        fold_summary=envelope.manifest.fold_summary,
        framework_version=envelope.manifest.framework_version,
        created_at_utc=envelope.manifest.created_at_utc,
    )
    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.write(
            PredictiveDatasetEnvelope(
                manifest=bad_manifest,
                features=envelope.features,
                folds=envelope.folds,
            )
        )


def test_derive_dataset_id_uses_fingerprint_prefix() -> None:
    fingerprint = "0123456789abcdef" + ("f" * 48)
    assert derive_dataset_id(fingerprint) == "0123456789abcdef"
