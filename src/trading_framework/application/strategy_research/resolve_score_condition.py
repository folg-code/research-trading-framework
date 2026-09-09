"""Resolve a declared score condition into a usable, promotable-family scorer.

Sprint 058 T003 (Phase 16 increment 16C), ADR-0033. Resolution happens once,
at config load time -- never lazily, never inside the simulation loop
(§13H.8's binding rule: ML enters simulation only through explicit strategy
semantics, never by loading model binaries). Two failure modes are refused
with distinguishable, named errors, per ADR-0033 §2:

    (a) no promoted artifact exists at the declared fingerprint
    (b) an artifact exists but its ``model_family`` is outside the strategy-
        gate allow-list (``MODEL_FAMILY_ALLOWLIST``)

Failure mode (b) is defense-in-depth, not the primary gate: promotion itself
(ADR-0029 §1) already refuses to produce an artifact for a non-promotable
family, so under normal operation every fingerprint under ``promoted/``
already names a promotable family. This check exists so a hand-edited or
otherwise corrupted manifest cannot silently become a strategy gate — it is
what makes TD-029's re-deferral (Q6 = Option B) a written, tested fact.

This module reads only ``manifest.json`` -- never ``artifact.json`` (the
parameter payload) and never ``models/fold_{n}.bin`` (TD-022's safe
operating boundary, unchanged). It imports nothing from
``infrastructure.ml`` (enforced by
``tests/unit/test_architecture_boundaries.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import promoted_artifact_manifest_path
from trading_framework.research.datasets.promoted_artifact import (
    MODEL_FAMILY_ALLOWLIST,
    PromotedArtifactManifest,
    PromotedArtifactRef,
    PromotedArtifactRepository,
)
from trading_framework.strategy.score_condition import ScoreConditionSpec


class ScoreConditionResolutionError(ValidationError):
    """Base class for score-condition resolution failures. Not raised directly."""


class ScoreConditionNotFoundError(ScoreConditionResolutionError):
    """No promoted artifact exists at the declared ``artifact_fingerprint``."""


class ScoreConditionFamilyRefusedError(ScoreConditionResolutionError):
    """A promoted artifact exists but names a non-promotable ``model_family``."""


@dataclass(frozen=True, slots=True)
class ResolvedScoreCondition:
    """A score condition whose promoted artifact is confirmed to exist and
    name a promotable family -- ready for evaluation (Sprint 058 T004), never
    a bare blob (TD-022's promotion branch).
    """

    spec: ScoreConditionSpec
    manifest: PromotedArtifactManifest


def resolve_score_condition(
    spec: ScoreConditionSpec,
    *,
    storage_root: Path,
    repository: PromotedArtifactRepository | None = None,
) -> ResolvedScoreCondition:
    """Resolve ``spec`` once, refusing with a named, distinguishable error.

    The family check reads the manifest's raw JSON directly, deliberately
    ahead of ``PromotedArtifactManifest.from_dict``'s own construction-time
    allow-list guard (``research/datasets/promoted_artifact.py``) --that
    guard raises a generic ``ValidationError`` indistinguishable from any
    other manifest-shape defect, which cannot satisfy ADR-0033 §2's
    requirement of two distinguishable failure modes. This function's own
    checks run first; a manifest that passes both is then read through the
    ordinary, fully-validating path.
    """
    manifest_path = promoted_artifact_manifest_path(storage_root, spec.artifact_fingerprint)
    if not manifest_path.is_file():
        msg = (
            f"no promoted artifact found for fingerprint "
            f"{spec.artifact_fingerprint!r} under {manifest_path.parent}"
        )
        raise ScoreConditionNotFoundError(msg)

    raw = _read_manifest_json(manifest_path)
    model_family = raw.get("model_family")
    if model_family not in MODEL_FAMILY_ALLOWLIST:
        msg = (
            f"promoted artifact {spec.artifact_fingerprint!r} names model_family "
            f"{model_family!r}, outside the strategy-gate allow-list "
            f"{sorted(MODEL_FAMILY_ALLOWLIST)} -- tree and neural scorers are "
            "research-only and may not gate a strategy "
            "(Phase 16 roadmap §13H.12 Q6, Option B; TD-029 stays deferred to 16G)"
        )
        raise ScoreConditionFamilyRefusedError(msg)

    active_repository = repository or PromotedArtifactRepository(storage_root)
    manifest = active_repository.read_manifest(
        PromotedArtifactRef(artifact_fingerprint=spec.artifact_fingerprint)
    )
    return ResolvedScoreCondition(spec=spec, manifest=manifest)


def _read_manifest_json(manifest_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"promoted artifact manifest is not valid JSON: {manifest_path}"
        raise ScoreConditionResolutionError(msg) from exc
    if not isinstance(raw, dict):
        msg = f"promoted artifact manifest must be a JSON object: {manifest_path}"
        raise ScoreConditionResolutionError(msg)
    return raw
