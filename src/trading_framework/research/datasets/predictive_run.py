"""Predictive Research run envelope — manifest, fingerprint, persistence."""

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
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_dir,
    predictive_research_run_model_path,
)
from trading_framework.research.predictive.estimators import EstimatorSpec
from trading_framework.research.predictive.preprocessing import PreprocessingSpec
from trading_framework.time.models.utc_instant import require_utc_aware

PREDICTIVE_RUN_SCHEMA_VERSION = "predictive_run.v1"
RUN_ID_HEX_LENGTH = 16
PREDICTION_COLUMNS = (
    "entity_id",
    "fold_id",
    "y_true",
    "y_pred",
    "y_proba",
    "forward_return",
)


@dataclass(frozen=True, slots=True)
class PredictiveRunRef:
    """Logical reference to one persisted Predictive Research run."""

    run_id: str

    def __post_init__(self) -> None:
        normalized = self.run_id.strip()
        if not normalized:
            msg = "run_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.run_id:
            object.__setattr__(self, "run_id", normalized)


@dataclass(frozen=True, slots=True)
class PredictiveRunManifest:
    """Run-level metadata for one Predictive Research envelope."""

    schema_version: str
    run_id: str
    run_fingerprint: str
    dataset_id: str
    dataset_fingerprint: str
    estimator_spec: dict[str, Any]
    preprocessing_spec: dict[str, Any]
    library: str
    library_version: str
    framework_version: str
    created_at_utc: datetime
    model_files: dict[str, str]
    estimator_description: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", require_utc_aware(self.created_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "run_fingerprint": self.run_fingerprint,
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "estimator_spec": dict(self.estimator_spec),
            "preprocessing_spec": dict(self.preprocessing_spec),
            "library": self.library,
            "library_version": self.library_version,
            "framework_version": self.framework_version,
            "created_at_utc": self.created_at_utc.isoformat(),
            "models": {
                "serializer": "joblib",
                "policy": (
                    "opaque; tagged with library name and version; "
                    "reproduce by re-fitting from this manifest, never by deserializing blobs"
                ),
                "files": dict(self.model_files),
            },
            "estimator_description": dict(self.estimator_description),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PredictiveRunManifest:
        estimator_spec = payload.get("estimator_spec", {})
        preprocessing_spec = payload.get("preprocessing_spec", {})
        estimator_description = payload.get("estimator_description", {})
        models = payload.get("models", {})
        if not isinstance(estimator_spec, dict):
            msg = "manifest estimator_spec must be a mapping"
            raise ValidationError(msg)
        if not isinstance(preprocessing_spec, dict):
            msg = "manifest preprocessing_spec must be a mapping"
            raise ValidationError(msg)
        if not isinstance(estimator_description, dict):
            msg = "manifest estimator_description must be a mapping"
            raise ValidationError(msg)
        if not isinstance(models, dict):
            msg = "manifest models must be a mapping"
            raise ValidationError(msg)
        files_raw = models.get("files", {})
        if not isinstance(files_raw, dict):
            msg = "manifest models.files must be a mapping"
            raise ValidationError(msg)
        return cls(
            schema_version=str(payload["schema_version"]),
            run_id=str(payload["run_id"]),
            run_fingerprint=str(payload["run_fingerprint"]),
            dataset_id=str(payload["dataset_id"]),
            dataset_fingerprint=str(payload["dataset_fingerprint"]),
            estimator_spec=dict(estimator_spec),
            preprocessing_spec=dict(preprocessing_spec),
            library=str(payload["library"]),
            library_version=str(payload["library_version"]),
            framework_version=str(payload["framework_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
            model_files={str(fold_id): str(path) for fold_id, path in files_raw.items()},
            estimator_description=dict(estimator_description),
        )


@dataclass(frozen=True, slots=True)
class PredictiveRunEnvelope:
    """In-memory Predictive Research run envelope.

    Durable facts are predictions and the manifest. Fitted model blobs are
    opaque sidecars and are not loaded by ``read()``.
    """

    manifest: PredictiveRunManifest
    predictions: pl.DataFrame


def compute_run_fingerprint(
    *,
    dataset_fingerprint: str,
    estimator_spec: EstimatorSpec,
    preprocessing_spec: PreprocessingSpec,
    library: str,
    library_version: str,
    framework_version: str,
) -> str:
    """SHA-256 fingerprint of the declared run identity (D-S040-18).

    Prediction rows and fitted blobs are never hashed. A library upgrade
    changes the fingerprint by design.
    """
    payload = {
        "dataset_fingerprint": dataset_fingerprint,
        "estimator_spec": estimator_spec.to_dict(),
        "preprocessing_spec": preprocessing_spec.identity_payload(),
        "library": library,
        "library_version": library_version,
        "framework_version": framework_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_predictive_run_id(fingerprint: str) -> str:
    """Return a 16-character hex prefix of the run fingerprint.

    Matches dataset_id and Signal Research ``derive_run_id``.
    """
    normalized = fingerprint.strip().lower()
    if len(normalized) < RUN_ID_HEX_LENGTH:
        msg = "run fingerprint must be at least 16 hex characters"
        raise ValidationError(msg)
    return normalized[:RUN_ID_HEX_LENGTH]


def validate_predictions_dataframe(frame: pl.DataFrame) -> None:
    """Require the prediction-table columns (TEST rows only)."""
    missing = [name for name in PREDICTION_COLUMNS if name not in frame.columns]
    if missing:
        msg = f"predictions missing required column: {missing[0]}"
        raise ValidationError(msg)


class PredictiveRunRepository:
    """Persist and load Predictive Research run envelopes.

    ``write`` stores opaque model bytes as ``models/fold_{n}.bin``. ``read``
    loads manifest + predictions only and never deserializes blobs.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(
        self,
        envelope: PredictiveRunEnvelope,
        *,
        model_blobs: Mapping[int, bytes],
    ) -> PredictiveRunRef:
        """Persist one run envelope; refuse overwrite of an existing run."""
        validate_predictions_dataframe(envelope.predictions)
        if not envelope.manifest.run_id.strip():
            msg = "manifest run_id must be non-empty"
            raise ValidationError(msg)
        if envelope.manifest.schema_version != PREDICTIVE_RUN_SCHEMA_VERSION:
            msg = f"unsupported schema version: {envelope.manifest.schema_version}"
            raise ValidationError(msg)

        run_dir = predictive_research_run_dir(self._root, envelope.manifest.run_id)
        if run_dir.exists():
            msg = f"run directory already exists: {run_dir}"
            raise FileExistsError(msg)

        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "manifest.json").write_text(
            json.dumps(envelope.manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        envelope.predictions.select(list(PREDICTION_COLUMNS)).write_parquet(
            run_dir / "predictions.parquet"
        )
        for fold_id, blob in sorted(model_blobs.items()):
            path = predictive_research_run_model_path(self._root, envelope.manifest.run_id, fold_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        return PredictiveRunRef(run_id=envelope.manifest.run_id)

    def read(self, ref: PredictiveRunRef) -> PredictiveRunEnvelope:
        """Load predictions and manifest. Do not load model blobs."""
        run_dir = predictive_research_run_dir(self._root, ref.run_id)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            msg = f"missing manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        manifest = PredictiveRunManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != PREDICTIVE_RUN_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        predictions_path = run_dir / "predictions.parquet"
        if not predictions_path.exists():
            msg = f"missing predictions parquet: {predictions_path}"
            raise FileNotFoundError(msg)
        predictions = pl.read_parquet(predictions_path)
        if "fold_id" in predictions.columns:
            predictions = predictions.with_columns(pl.col("fold_id").cast(pl.Int64))
        validate_predictions_dataframe(predictions)
        return PredictiveRunEnvelope(manifest=manifest, predictions=predictions)
