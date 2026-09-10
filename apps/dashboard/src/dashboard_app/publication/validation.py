"""Fail-closed resolution of a study manifest against a projection bundle.

Streamlit callers never catch a raised :mod:`dashboard_app.publication.errors`
exception directly on the render path -- these functions return a plain
Result-like value instead, so an absent bundle, a schema mismatch, or a
manifest naming an artifact the bundle does not contain each become an
explicit :class:`PublicationUnavailable` state (ADR-0034 S1.6, S2.4), never a
fallback to scanning the workspace and never a silently missing role.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_app.publication.errors import InvalidProjectionSchemaError
from dashboard_app.publication.manifest import (
    PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
    PortfolioStudyManifest,
)
from dashboard_app.publication.projection import ProjectedArtifact, PublicProjectionBundle


@dataclass(frozen=True, slots=True)
class StudyEvidence:
    """A validated manifest paired with its fully resolved artifacts."""

    manifest: PortfolioStudyManifest
    resolved_artifacts: Mapping[str, ProjectedArtifact]


@dataclass(frozen=True, slots=True)
class PublicationUnavailable:
    """An explicit unavailable/invalid publication state.

    ``reason`` is one of a small closed set of reason codes:
    ``"bundle_missing"``, ``"manifest_missing"``, ``"schema_mismatch"``,
    ``"dangling_reference"``, ``"catalog_invalid"``.
    """

    reason: str
    detail: str


def load_projection_bundle(
    payload: Mapping[str, Any] | None,
) -> PublicProjectionBundle | PublicationUnavailable:
    """Parse a raw projection bundle payload, failing closed on any problem.

    ``payload=None`` (bundle absent, e.g. the generator step was skipped)
    returns ``PublicationUnavailable(reason="bundle_missing")``. A schema
    mismatch or malformed payload is caught here and converted rather than
    left to propagate as a raised exception.
    """
    if payload is None:
        return PublicationUnavailable(
            reason="bundle_missing",
            detail="no public projection bundle payload was supplied",
        )

    try:
        return PublicProjectionBundle.from_dict(payload)
    except InvalidProjectionSchemaError as exc:
        return PublicationUnavailable(reason="schema_mismatch", detail=str(exc))


def load_projection_bundle_from_path(path: Path) -> PublicProjectionBundle | PublicationUnavailable:
    """Read and parse a committed projection bundle file, failing closed.

    A missing file is ``PublicationUnavailable(reason="bundle_missing")`` --
    the same reason :func:`load_projection_bundle` uses for an absent
    payload, since from a caller's perspective the bundle is equally
    unavailable either way.
    """
    if not path.is_file():
        return PublicationUnavailable(
            reason="bundle_missing", detail=f"projection bundle file not found: {path}"
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return PublicationUnavailable(reason="schema_mismatch", detail=str(exc))

    return load_projection_bundle(payload)


def load_study_manifest(
    payload: Mapping[str, Any] | None,
) -> PortfolioStudyManifest | PublicationUnavailable:
    """Parse a raw study manifest payload, failing closed on any problem.

    ``payload=None`` returns ``PublicationUnavailable(reason="manifest_missing")``.
    A malformed payload (missing required field, an invalid ``maturity`` or
    ``workflows`` value) is caught here and converted rather than left to
    propagate as a raised exception.
    """
    if payload is None:
        return PublicationUnavailable(
            reason="manifest_missing", detail="no study manifest payload was supplied"
        )

    if payload.get("schema_version") != PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION:
        return PublicationUnavailable(
            reason="schema_mismatch",
            detail=(
                f"unsupported study manifest schema_version: {payload.get('schema_version')!r}"
            ),
        )

    try:
        return PortfolioStudyManifest.from_dict(payload)
    except (KeyError, ValueError) as exc:
        return PublicationUnavailable(reason="schema_mismatch", detail=str(exc))


def load_study_manifest_from_path(path: Path) -> PortfolioStudyManifest | PublicationUnavailable:
    """Read and parse a hand-authored study manifest file, failing closed."""
    if not path.is_file():
        return PublicationUnavailable(
            reason="manifest_missing", detail=f"study manifest file not found: {path}"
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return PublicationUnavailable(reason="schema_mismatch", detail=str(exc))

    return load_study_manifest(payload)


def resolve_study_evidence(
    manifest: PortfolioStudyManifest, bundle: PublicProjectionBundle
) -> StudyEvidence | PublicationUnavailable:
    """Resolve every role in ``manifest.artifact_roles`` against ``bundle``.

    Fails closed: any ``artifact_id`` named in ``artifact_roles`` that is
    absent from ``bundle.artifacts`` returns
    ``PublicationUnavailable(reason="dangling_reference")`` for the whole
    study -- never a raise, and never a bundle that silently omits the
    missing role (ADR-0034 S2.4).
    """
    resolved: dict[str, ProjectedArtifact] = {}
    for role, artifact_id in manifest.artifact_roles.items():
        artifact = bundle.artifacts.get(artifact_id)
        if artifact is None:
            return PublicationUnavailable(
                reason="dangling_reference",
                detail=(
                    f"study {manifest.slug!r} role {role!r} names artifact_id "
                    f"{artifact_id!r}, which is absent from the projection bundle"
                ),
            )
        resolved[role] = artifact

    return StudyEvidence(manifest=manifest, resolved_artifacts=resolved)
