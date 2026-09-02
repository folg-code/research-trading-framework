"""Promoted predictive artifact — manifest, fingerprint, content-addressed store.

A promoted artifact is a **separate category** from a Predictive Research run
(`research/datasets/predictive_run.py`): it is a content-addressed directory
under ``research/predictive_research/promoted/{artifact_fingerprint}/``
containing exactly two files — ``manifest.json`` (this module's
``PromotedArtifactManifest``) and ``artifact.json`` (the parameter payload,
defined by ``research/predictive/promotion``, Wave 2). No registry, no index
file, no ``latest`` pointer, no lifecycle/status field exists anywhere in this
module or the directory it manages (ADR-0024 condition 5; ADR-0029 §2;
D-S049-03).

This module imports no ML library (sklearn / xgboost / lightgbm / catboost /
torch). ``infrastructure/ml/promotion.py`` is the only place that touches
scikit-learn, behind lazy imports (ADR-0029 §9, D-S049-08).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    promoted_artifact_dir,
    promoted_artifact_manifest_path,
    promoted_artifact_payload_path,
)
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.time.models.utc_instant import require_utc_aware

PROMOTED_ARTIFACT_SCHEMA_VERSION = "promoted_artifact.v1"

#: Linear/logistic families only in v1 (D-S049-13). Promotion of a tree or
#: neural family is refused elsewhere (T006b/T008); this allow-list is the
#: contract-level guard that a manifest can never even *describe* one.
MODEL_FAMILY_ALLOWLIST = frozenset(
    {
        "sklearn.ridge",
        "sklearn.elastic_net",
        "sklearn.logistic",
    }
)

_REQUIRED_MANIFEST_FIELDS = (
    "schema_version",
    "artifact_fingerprint",
    "run_fingerprint",
    "dataset_fingerprint",
    "fold_id",
    "features",
    "model_family",
    "format",
    "format_version",
    "preprocessing_spec",
    "estimator_spec",
    "training_library",
    "training_library_version",
    "created_at_utc",
)


@dataclass(frozen=True, slots=True)
class PromotedArtifactRef:
    """Logical reference to one persisted promoted artifact, by fingerprint."""

    artifact_fingerprint: str

    def __post_init__(self) -> None:
        normalized = self.artifact_fingerprint.strip()
        if not normalized:
            msg = "artifact_fingerprint must be non-empty"
            raise ValidationError(msg)
        if normalized != self.artifact_fingerprint:
            object.__setattr__(self, "artifact_fingerprint", normalized)


@dataclass(frozen=True, slots=True)
class PromotedArtifactManifest:
    """Manifest for one promoted predictive artifact (ADR-0029 §2).

    ``feature_output_refs`` is the **ordered** list of feature ``OutputRef``
    identities (``OutputRef.canonical_key()`` strings) that fed the promoted
    model, positional per ADR-0029 §1 — the evaluator's column order is
    positional, so this order is part of the artifact's meaning, not
    incidental metadata.

    ``training_library`` / ``training_library_version`` are recorded for
    **provenance only** and are never a load-time gate (D-S049-07): a
    parameter file has no coupling to scikit-learn, because scikit-learn is
    not involved in reading it, so a training-library version difference does
    not refuse a *load*. The version that IS enforced is checked once, at
    *promotion* time, before any blob is unpickled — the promotion-time
    guard in ``infrastructure/ml/promotion.py`` (ADR-0029 §4).
    """

    schema_version: str
    artifact_fingerprint: str
    run_fingerprint: str
    dataset_fingerprint: str
    fold_id: int
    feature_output_refs: tuple[str, ...]
    model_family: str
    format: str
    format_version: str
    preprocessing_spec: dict[str, Any]
    estimator_spec: dict[str, Any]
    training_library: str
    training_library_version: str
    created_at_utc: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", require_utc_aware(self.created_at_utc))
        if self.model_family not in MODEL_FAMILY_ALLOWLIST:
            msg = (
                f"model_family {self.model_family!r} is outside the allow-list: "
                f"{sorted(MODEL_FAMILY_ALLOWLIST)}"
            )
            raise ValidationError(msg)
        if not self.feature_output_refs:
            msg = "feature_output_refs must be non-empty"
            raise ValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_fingerprint": self.artifact_fingerprint,
            "run_fingerprint": self.run_fingerprint,
            "dataset_fingerprint": self.dataset_fingerprint,
            "fold_id": self.fold_id,
            "features": list(self.feature_output_refs),
            "model_family": self.model_family,
            "format": self.format,
            "format_version": self.format_version,
            "preprocessing_spec": dict(self.preprocessing_spec),
            "estimator_spec": dict(self.estimator_spec),
            "training_library": self.training_library,
            "training_library_version": self.training_library_version,
            "created_at_utc": self.created_at_utc.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PromotedArtifactManifest:
        for field in _REQUIRED_MANIFEST_FIELDS:
            if field not in payload:
                msg = f"manifest missing required field: {field}"
                raise ValidationError(msg)

        preprocessing_spec = payload["preprocessing_spec"]
        estimator_spec = payload["estimator_spec"]
        features = payload["features"]
        if not isinstance(preprocessing_spec, dict):
            msg = "manifest preprocessing_spec must be a mapping"
            raise ValidationError(msg)
        if not isinstance(estimator_spec, dict):
            msg = "manifest estimator_spec must be a mapping"
            raise ValidationError(msg)
        if not isinstance(features, list):
            msg = "manifest features must be a sequence"
            raise ValidationError(msg)

        return cls(
            schema_version=str(payload["schema_version"]),
            artifact_fingerprint=str(payload["artifact_fingerprint"]),
            run_fingerprint=str(payload["run_fingerprint"]),
            dataset_fingerprint=str(payload["dataset_fingerprint"]),
            fold_id=int(payload["fold_id"]),
            feature_output_refs=tuple(str(item) for item in features),
            model_family=str(payload["model_family"]),
            format=str(payload["format"]),
            format_version=str(payload["format_version"]),
            preprocessing_spec=dict(preprocessing_spec),
            estimator_spec=dict(estimator_spec),
            training_library=str(payload["training_library"]),
            training_library_version=str(payload["training_library_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
        )


def compute_promoted_artifact_fingerprint(
    *,
    run_fingerprint: str,
    fold_id: int,
    format: str,  # matches the domain vocabulary (ADR-0029 §2)
    format_version: str,
    model_family: str,
    features: Sequence[OutputRef] | Sequence[str],
    preprocessing_spec: Mapping[str, Any],
    estimator_spec: Mapping[str, Any],
) -> str:
    """SHA-256 fingerprint of a promoted artifact's declared identity (D-S049-05).

    Mirrors ``compute_run_fingerprint``'s canonicalization exactly: SHA-256 over
    ``json.dumps(payload, sort_keys=True, separators=(",", ":"))``.

    Hashed: ``run_fingerprint``, ``fold_id``, ``format``, ``format_version``,
    ``model_family``, the ordered feature ``OutputRef`` identities, and both
    specs. ``features`` may be passed as ``OutputRef`` objects (their
    ``canonical_key()`` is hashed) or as pre-derived identity strings; either
    way feature **order is preserved, not sorted** — the evaluator's column
    order is positional, so a permutation is a different artifact.

    **Fitted parameter values are never hashed** — this is a deliberate
    identity choice (Q9 / D-S049-05), not an oversight: this function's
    signature has no coefficient/intercept/statistics parameter at all, so a
    perturbed fitted value cannot reach the payload. Identity is "which run,
    which fold, which spec", not "which numbers came out of the fit."
    """
    feature_identities = [
        feature.canonical_key() if isinstance(feature, OutputRef) else str(feature)
        for feature in features
    ]
    payload: dict[str, Any] = {
        "run_fingerprint": run_fingerprint,
        "fold_id": fold_id,
        "format": format,
        "format_version": format_version,
        "model_family": model_family,
        "features": feature_identities,
        "preprocessing_spec": dict(preprocessing_spec),
        "estimator_spec": dict(estimator_spec),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PromotedArtifactRepository:
    """Persist and load promoted artifacts.

    ``write`` refuses to overwrite an existing content-addressed directory.
    ``read_manifest`` loads only ``manifest.json`` — it never reads the
    parameter payload (``artifact.json``), so it succeeds even when the
    payload is corrupt or absent. No registry, index file, or lifecycle field
    is written or read anywhere in this class (ADR-0024 condition 5).
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(
        self,
        manifest: PromotedArtifactManifest,
        *,
        artifact_payload: Mapping[str, Any],
    ) -> PromotedArtifactRef:
        """Persist one promoted artifact; refuse overwrite of an existing one."""
        if manifest.schema_version != PROMOTED_ARTIFACT_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        artifact_dir = promoted_artifact_dir(self._root, manifest.artifact_fingerprint)
        if artifact_dir.exists():
            msg = f"promoted artifact directory already exists: {artifact_dir}"
            raise FileExistsError(msg)

        artifact_dir.mkdir(parents=True, exist_ok=False)
        promoted_artifact_manifest_path(self._root, manifest.artifact_fingerprint).write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        promoted_artifact_payload_path(self._root, manifest.artifact_fingerprint).write_text(
            json.dumps(dict(artifact_payload), indent=2),
            encoding="utf-8",
        )
        return PromotedArtifactRef(artifact_fingerprint=manifest.artifact_fingerprint)

    def read_manifest(self, ref: PromotedArtifactRef) -> PromotedArtifactManifest:
        """Load the manifest only. Never reads or parses the parameter payload."""
        manifest_path = promoted_artifact_manifest_path(self._root, ref.artifact_fingerprint)
        if not manifest_path.exists():
            msg = f"missing promoted artifact manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        manifest = PromotedArtifactManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != PROMOTED_ARTIFACT_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)
        return manifest
