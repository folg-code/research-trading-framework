"""Predictive Research dataset envelope — manifest, fingerprint, persistence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import predictive_research_dataset_dir
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive.exclusions import MatrixExclusionCounts
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.time.models.utc_instant import require_utc_aware

PREDICTIVE_DATASET_SCHEMA_VERSION = "predictive_dataset.v1"
DATASET_ID_HEX_LENGTH = 16
_REQUIRED_FEATURE_COLUMNS = (
    "entity_id",
    "horizon_bars",
    "detected_at",
    "available_at",
    "label_end_at",
    "label",
    "forward_return",
    "outcome_status",
    "fold_id",
    "fold_role",
)
_UTC_DATETIME_COLUMNS = frozenset({"detected_at", "available_at", "label_end_at"})
_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_VALID_FOLD_ROLES = frozenset(role.value for role in FoldRole)


@dataclass(frozen=True, slots=True)
class PredictiveDatasetRef:
    """Logical reference to one persisted Predictive Research dataset."""

    dataset_id: str

    def __post_init__(self) -> None:
        normalized = self.dataset_id.strip()
        if not normalized:
            msg = "dataset_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.dataset_id:
            object.__setattr__(self, "dataset_id", normalized)


@dataclass(frozen=True, slots=True)
class ResolvedFoldBoundary:
    """Observed fold window and role counts from assigned labelled rows."""

    fold_id: int
    test_start: datetime
    test_end: datetime
    train_start: datetime | None
    embargo_end: datetime | None
    role_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "train_start": None if self.train_start is None else self.train_start.isoformat(),
            "embargo_end": None if self.embargo_end is None else self.embargo_end.isoformat(),
            "role_counts": dict(self.role_counts),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ResolvedFoldBoundary:
        train_start_raw = payload.get("train_start")
        embargo_end_raw = payload.get("embargo_end")
        role_counts_raw = payload.get("role_counts", {})
        if not isinstance(role_counts_raw, dict):
            msg = "fold role_counts must be a mapping"
            raise ValidationError(msg)
        return cls(
            fold_id=int(payload["fold_id"]),
            test_start=datetime.fromisoformat(str(payload["test_start"])),
            test_end=datetime.fromisoformat(str(payload["test_end"])),
            train_start=(
                None if train_start_raw is None else datetime.fromisoformat(str(train_start_raw))
            ),
            embargo_end=(
                None if embargo_end_raw is None else datetime.fromisoformat(str(embargo_end_raw))
            ),
            role_counts={str(role): int(count) for role, count in role_counts_raw.items()},
        )


@dataclass(frozen=True, slots=True)
class PredictiveDatasetManifest:
    """Dataset-level metadata for one Predictive Research envelope."""

    schema_version: str
    dataset_id: str
    study_spec: dict[str, Any]
    definition_hash: str
    dataset_fingerprint: str
    source_dataset_ref: str
    time_range_start: datetime
    time_range_end: datetime
    exclusion_counts: dict[str, int]
    fold_summary: dict[str, Any]
    framework_version: str
    created_at_utc: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", require_utc_aware(self.created_at_utc))
        object.__setattr__(self, "time_range_start", require_utc_aware(self.time_range_start))
        object.__setattr__(self, "time_range_end", require_utc_aware(self.time_range_end))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "study_spec": self.study_spec,
            "definition_hash": self.definition_hash,
            "dataset_fingerprint": self.dataset_fingerprint,
            "source_dataset_ref": self.source_dataset_ref,
            "time_range": {
                "start": self.time_range_start.isoformat(),
                "end": self.time_range_end.isoformat(),
            },
            "exclusion_counts": dict(self.exclusion_counts),
            "fold_summary": dict(self.fold_summary),
            "framework_version": self.framework_version,
            "created_at_utc": self.created_at_utc.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PredictiveDatasetManifest:
        time_payload = payload.get("time_range")
        if not isinstance(time_payload, dict):
            msg = "manifest time_range must be a mapping"
            raise ValidationError(msg)
        exclusion_counts = payload.get("exclusion_counts", {})
        fold_summary = payload.get("fold_summary", {})
        study_spec = payload.get("study_spec", {})
        if not isinstance(exclusion_counts, dict):
            msg = "manifest exclusion_counts must be a mapping"
            raise ValidationError(msg)
        if not isinstance(fold_summary, dict):
            msg = "manifest fold_summary must be a mapping"
            raise ValidationError(msg)
        if not isinstance(study_spec, dict):
            msg = "manifest study_spec must be a mapping"
            raise ValidationError(msg)
        return cls(
            schema_version=str(payload["schema_version"]),
            dataset_id=str(payload["dataset_id"]),
            study_spec=dict(study_spec),
            definition_hash=str(payload["definition_hash"]),
            dataset_fingerprint=str(payload["dataset_fingerprint"]),
            source_dataset_ref=str(payload["source_dataset_ref"]),
            time_range_start=datetime.fromisoformat(str(time_payload["start"])),
            time_range_end=datetime.fromisoformat(str(time_payload["end"])),
            exclusion_counts={str(key): int(value) for key, value in exclusion_counts.items()},
            fold_summary=dict(fold_summary),
            framework_version=str(payload["framework_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
        )


@dataclass(frozen=True, slots=True)
class PredictiveDatasetEnvelope:
    """In-memory Predictive Research dataset envelope."""

    manifest: PredictiveDatasetManifest
    features: pl.DataFrame
    folds: tuple[ResolvedFoldBoundary, ...]


def compute_dataset_fingerprint(
    *,
    definition_hash: str,
    feature_lineage: Mapping[str, OutputRef],
    dataset_ref: DatasetRef | str,
    time_range: TimeRange,
) -> str:
    """SHA-256 fingerprint of spec, feature lineage, dataset ref, and time range.

    Materialized frame bytes are never hashed (D-S039-11): Polars versions can
    change physical encodings without changing the learning problem.
    """
    lineage_payload = {
        alias: output_ref.canonical_key()
        for alias, output_ref in sorted(feature_lineage.items(), key=lambda item: item[0])
    }
    payload = {
        "definition_hash": definition_hash,
        "feature_lineage": lineage_payload,
        "dataset_ref": str(dataset_ref),
        "time_range": {
            "start": time_range.start.isoformat(),
            "end": time_range.end.isoformat(),
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_dataset_id(fingerprint: str) -> str:
    """Return a 16-character hex prefix of the dataset fingerprint.

    Matches Signal Research ``derive_run_id``: storage directories use the
    short prefix; the full SHA-256 hex lives on the manifest.
    """
    normalized = fingerprint.strip().lower()
    if len(normalized) < DATASET_ID_HEX_LENGTH:
        msg = "dataset fingerprint must be at least 16 hex characters"
        raise ValidationError(msg)
    return normalized[:DATASET_ID_HEX_LENGTH]


def exclusion_counts_to_dict(counts: MatrixExclusionCounts) -> dict[str, int]:
    """Serialize labelled-matrix exclusion counts for the manifest."""
    return {
        "candidate_rows": counts.candidate_rows,
        "labelled_rows": counts.labelled_rows,
        "incomplete_horizon": counts.incomplete_horizon,
        "insufficient_data": counts.insufficient_data,
        "null_features": counts.null_features,
    }


def fold_summary_from_features(features: pl.DataFrame) -> dict[str, Any]:
    """Aggregate TRAIN / TEST / PURGED / EMBARGOED counts for the manifest."""
    _require_fold_columns(features)
    overall = {
        role: features.filter(pl.col("fold_role") == role).height
        for role in sorted(_VALID_FOLD_ROLES)
    }
    per_fold: list[dict[str, Any]] = []
    fold_ids = sorted(int(value) for value in features.get_column("fold_id").unique().to_list())
    for fold_id in fold_ids:
        fold_rows = features.filter(pl.col("fold_id") == fold_id)
        per_fold.append(
            {
                "fold_id": fold_id,
                **{
                    role: fold_rows.filter(pl.col("fold_role") == role).height
                    for role in sorted(_VALID_FOLD_ROLES)
                },
            }
        )
    return {
        "fold_count": len(fold_ids),
        "role_counts": overall,
        "per_fold": per_fold,
    }


def resolve_fold_boundaries(features: pl.DataFrame) -> tuple[ResolvedFoldBoundary, ...]:
    """Derive resolved fold windows from persisted ``available_at`` and roles."""
    _require_fold_columns(features)
    boundaries: list[ResolvedFoldBoundary] = []
    fold_ids = sorted(int(value) for value in features.get_column("fold_id").unique().to_list())
    for fold_id in fold_ids:
        fold_rows = features.filter(pl.col("fold_id") == fold_id)
        test_rows = fold_rows.filter(pl.col("fold_role") == FoldRole.TEST.value)
        if test_rows.height == 0:
            msg = f"fold {fold_id} has no TEST rows"
            raise ValidationError(msg)
        train_rows = fold_rows.filter(pl.col("fold_role") == FoldRole.TRAIN.value)
        embargo_rows = fold_rows.filter(pl.col("fold_role") == FoldRole.EMBARGOED.value)
        role_counts = {
            role: fold_rows.filter(pl.col("fold_role") == role).height
            for role in sorted(_VALID_FOLD_ROLES)
        }
        boundaries.append(
            ResolvedFoldBoundary(
                fold_id=fold_id,
                test_start=_require_datetime(test_rows.get_column("available_at").min()),
                test_end=_require_datetime(test_rows.get_column("available_at").max()),
                train_start=_optional_datetime(train_rows.get_column("available_at").min()),
                embargo_end=_optional_datetime(embargo_rows.get_column("available_at").max()),
                role_counts=role_counts,
            )
        )
    return tuple(boundaries)


def validate_features_dataframe(frame: pl.DataFrame) -> None:
    """Require fold-labelled feature-matrix columns and known fold roles."""
    missing = [name for name in _REQUIRED_FEATURE_COLUMNS if name not in frame.columns]
    if missing:
        msg = f"features missing required column: {missing[0]}"
        raise ValidationError(msg)
    roles = set(frame.get_column("fold_role").drop_nulls().to_list())
    unknown = roles - _VALID_FOLD_ROLES
    if unknown:
        msg = f"unsupported fold_role values: {sorted(str(role) for role in unknown)}"
        raise ValidationError(msg)


class PredictiveDatasetRepository:
    """Persist and load Predictive Research dataset envelopes."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(self, envelope: PredictiveDatasetEnvelope) -> PredictiveDatasetRef:
        """Persist one dataset envelope; refuse overwrite of an existing dataset."""
        validate_features_dataframe(envelope.features)
        if not envelope.manifest.dataset_id.strip():
            msg = "manifest dataset_id must be non-empty"
            raise ValidationError(msg)
        if envelope.manifest.schema_version != PREDICTIVE_DATASET_SCHEMA_VERSION:
            msg = f"unsupported schema version: {envelope.manifest.schema_version}"
            raise ValidationError(msg)

        dataset_dir = predictive_research_dataset_dir(self._root, envelope.manifest.dataset_id)
        if dataset_dir.exists():
            msg = f"dataset directory already exists: {dataset_dir}"
            raise FileExistsError(msg)

        dataset_dir.mkdir(parents=True, exist_ok=False)
        (dataset_dir / "manifest.json").write_text(
            json.dumps(envelope.manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        _ensure_utc_datetime_columns(envelope.features).write_parquet(
            dataset_dir / "features.parquet"
        )
        (dataset_dir / "folds.json").write_text(
            json.dumps([boundary.to_dict() for boundary in envelope.folds], indent=2),
            encoding="utf-8",
        )
        return PredictiveDatasetRef(dataset_id=envelope.manifest.dataset_id)

    def read(self, ref: PredictiveDatasetRef) -> PredictiveDatasetEnvelope:
        """Load one dataset envelope and validate schema version."""
        dataset_dir = predictive_research_dataset_dir(self._root, ref.dataset_id)
        manifest_path = dataset_dir / "manifest.json"
        if not manifest_path.exists():
            msg = f"missing manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        manifest = PredictiveDatasetManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != PREDICTIVE_DATASET_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        features_path = dataset_dir / "features.parquet"
        if not features_path.exists():
            msg = f"missing features parquet: {features_path}"
            raise FileNotFoundError(msg)
        features = _ensure_utc_datetime_columns(pl.read_parquet(features_path))
        validate_features_dataframe(features)

        folds_path = dataset_dir / "folds.json"
        if not folds_path.exists():
            msg = f"missing folds payload: {folds_path}"
            raise FileNotFoundError(msg)
        folds_payload = json.loads(folds_path.read_text(encoding="utf-8"))
        if not isinstance(folds_payload, list):
            msg = f"folds payload must be a sequence: {folds_path}"
            raise ValidationError(msg)
        folds = tuple(
            ResolvedFoldBoundary.from_dict({str(key): value for key, value in item.items()})
            for item in folds_payload
            if isinstance(item, dict)
        )
        if len(folds) != len(folds_payload):
            msg = f"folds payload entries must be mappings: {folds_path}"
            raise ValidationError(msg)
        return PredictiveDatasetEnvelope(manifest=manifest, features=features, folds=folds)


def _require_fold_columns(features: pl.DataFrame) -> None:
    for name in ("fold_id", "fold_role", "available_at"):
        if name not in features.columns:
            msg = f"features missing required column: {name}"
            raise ValidationError(msg)


def _require_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = "fold boundary timestamp must be a datetime"
        raise ValidationError(msg)
    return require_utc_aware(value)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return _require_datetime(value)


def _ensure_utc_datetime_columns(frame: pl.DataFrame) -> pl.DataFrame:
    casts: list[pl.Expr] = []
    for name, dtype in frame.schema.items():
        if name in _UTC_DATETIME_COLUMNS or isinstance(dtype, pl.Datetime):
            casts.append(pl.col(name).cast(_UTC_US))
        elif name == "fold_id":
            casts.append(pl.col(name).cast(pl.Int64))
    if not casts:
        return frame
    return frame.with_columns(casts)
