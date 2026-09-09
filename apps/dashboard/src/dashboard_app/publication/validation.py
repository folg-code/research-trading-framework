"""Fail-closed resolution of a study manifest against a projection bundle.

Streamlit callers never catch a raised :mod:`dashboard_app.publication.errors`
exception directly on the render path -- these functions return a plain
Result-like value instead, so an absent bundle, a schema mismatch, or a
manifest naming an artifact the bundle does not contain each become an
explicit :class:`PublicationUnavailable` state (ADR-0034 S1.6, S2.4), never a
fallback to scanning the workspace and never a silently missing role.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dashboard_app.publication.errors import InvalidProjectionSchemaError
from dashboard_app.publication.manifest import PortfolioStudyManifest
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
    ``"bundle_missing"``, ``"schema_mismatch"``, ``"dangling_reference"``.
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
