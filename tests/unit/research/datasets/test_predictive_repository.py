"""Tests for Predictive Research dataset repository round-trip."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import predictive_research_dataset_dir
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_V2,
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
    PredictiveTask,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    SampleKind,
    SampleProvenance,
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
            "forward_return": [0.01] * count,
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


def _sample_provenance() -> SampleProvenance:
    return SampleProvenance(
        kind=SampleKind.EVERY_BAR,
        task=PredictiveTask.FORWARD_RETURN,
        universe_row_count=40,
        resolved_row_count=40,
        drop_counts={},
    )


def _envelope(
    *,
    dataset_id: str = "0123456789abcdef",
    sample_provenance: SampleProvenance | None = None,
) -> PredictiveDatasetEnvelope:
    features = _assigned_features()
    created_at = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    return PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_V2,
            dataset_id=dataset_id,
            study_spec={"study_id": "atr_forward_return", "label": {"kind": "REGRESSION"}},
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
            sample_provenance=(
                _sample_provenance() if sample_provenance is None else sample_provenance
            ),
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
    assert loaded.manifest.sample_provenance == envelope.manifest.sample_provenance
    assert loaded.manifest.sample_provenance is not None
    assert loaded.manifest.sample_provenance.kind is SampleKind.EVERY_BAR
    assert loaded.manifest.sample_provenance.universe_row_count == 40
    assert loaded.manifest.sample_provenance.resolved_row_count == 40
    assert loaded.manifest.sample_provenance.drop_counts == {}
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


def test_repository_refuses_v2_manifest_without_sample_provenance(tmp_path: Path) -> None:
    """S056-T003: a v2 manifest must carry sample_provenance — no silent tolerance."""
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    envelope = _envelope()
    missing_provenance_manifest = PredictiveDatasetManifest(
        schema_version=PREDICTIVE_DATASET_SCHEMA_V2,
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
        sample_provenance=None,
    )
    with pytest.raises(ValidationError, match="requires sample_provenance"):
        repository.write(
            PredictiveDatasetEnvelope(
                manifest=missing_provenance_manifest,
                features=envelope.features,
                folds=envelope.folds,
            )
        )


def test_repository_reads_legacy_v1_manifest_without_sample_provenance(tmp_path: Path) -> None:
    """S056-T003 read-compat: a manifest persisted before this field existed still loads.

    ``sample_provenance`` is absent (never written by v1) rather than
    defaulted to a fabricated value — the manifest.json below is exactly the
    shape v1 code emitted, with no ``sample_provenance`` key at all.
    """
    storage_root = tmp_path / "workspace"
    envelope = _envelope(dataset_id="fedcba9876543210")
    dataset_dir = predictive_research_dataset_dir(storage_root, envelope.manifest.dataset_id)
    dataset_dir.mkdir(parents=True)

    legacy_payload = envelope.manifest.to_dict()
    legacy_payload["schema_version"] = PREDICTIVE_DATASET_SCHEMA_VERSION
    del legacy_payload["sample_provenance"]
    (dataset_dir / "manifest.json").write_text(
        json.dumps(legacy_payload, indent=2), encoding="utf-8"
    )
    envelope.features.write_parquet(dataset_dir / "features.parquet")
    (dataset_dir / "folds.json").write_text(
        json.dumps([boundary.to_dict() for boundary in envelope.folds], indent=2),
        encoding="utf-8",
    )

    repository = PredictiveDatasetRepository(storage_root)
    loaded = repository.read(PredictiveDatasetRef(dataset_id=envelope.manifest.dataset_id))

    assert loaded.manifest.schema_version == PREDICTIVE_DATASET_SCHEMA_VERSION
    assert loaded.manifest.sample_provenance is None
    assert loaded.manifest.exclusion_counts["candidate_rows"] == 40


def test_repository_can_still_write_v1_manifest_without_sample_provenance(
    tmp_path: Path,
) -> None:
    """v1 stays a valid WRITE target too (mirrors signal_research's v1/v2 split);

    nothing in this codebase writes it anymore after this sprint, but the
    format itself is not refused.
    """
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    envelope = _envelope(dataset_id="1111222233334444")
    v1_manifest = PredictiveDatasetManifest(
        schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
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
        sample_provenance=None,
    )

    ref = repository.write(
        PredictiveDatasetEnvelope(
            manifest=v1_manifest, features=envelope.features, folds=envelope.folds
        )
    )
    loaded = repository.read(ref)

    assert loaded.manifest.schema_version == PREDICTIVE_DATASET_SCHEMA_VERSION
    assert loaded.manifest.sample_provenance is None


def test_dataset_fingerprint_identical_across_different_sample_provenance(
    tmp_path: Path,
) -> None:
    """S056-T003 / ADR-0031 Decision 6: provenance never enters the fingerprint."""
    storage_root = tmp_path / "workspace"
    repository = PredictiveDatasetRepository(storage_root)
    without_signal_context = _envelope(
        dataset_id="aaaaaaaaaaaaaaaa",
        sample_provenance=SampleProvenance(
            kind=SampleKind.EVERY_BAR,
            task=PredictiveTask.FORWARD_RETURN,
            universe_row_count=40,
            resolved_row_count=40,
            drop_counts={},
        ),
    )
    with_dropped_rows = _envelope(
        dataset_id="bbbbbbbbbbbbbbbb",
        sample_provenance=SampleProvenance(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            task=PredictiveTask.SIGNAL_QUALITY,
            universe_row_count=40,
            resolved_row_count=12,
            drop_counts={"incomplete_horizon": 20, "outside_range": 8},
        ),
    )
    # Same fingerprint value on both manifests (as computed by
    # compute_dataset_fingerprint over definition_hash/lineage/dataset_ref/
    # time_range, none of which involve sample_provenance).
    shared_fingerprint = "c" * 64
    without_signal_context = PredictiveDatasetEnvelope(
        manifest=replace(without_signal_context.manifest, dataset_fingerprint=shared_fingerprint),
        features=without_signal_context.features,
        folds=without_signal_context.folds,
    )
    with_dropped_rows = PredictiveDatasetEnvelope(
        manifest=replace(with_dropped_rows.manifest, dataset_fingerprint=shared_fingerprint),
        features=with_dropped_rows.features,
        folds=with_dropped_rows.folds,
    )

    repository.write(without_signal_context)
    repository.write(with_dropped_rows)
    loaded_a = repository.read(
        PredictiveDatasetRef(dataset_id=without_signal_context.manifest.dataset_id)
    )
    loaded_b = repository.read(
        PredictiveDatasetRef(dataset_id=with_dropped_rows.manifest.dataset_id)
    )

    assert loaded_a.manifest.dataset_fingerprint == shared_fingerprint
    assert loaded_b.manifest.dataset_fingerprint == shared_fingerprint
    assert loaded_a.manifest.dataset_fingerprint == loaded_b.manifest.dataset_fingerprint
    assert loaded_a.manifest.sample_provenance != loaded_b.manifest.sample_provenance
