"""Public projection generator (ADR-0034 S1.2).

Orchestration only: given already-loaded raw artifact payloads, look up the
matching sanitizer by role, wrap each sanitized result in a
:class:`~dashboard_app.publication.projection.ProjectedArtifact`, and
assemble a :class:`~dashboard_app.publication.projection.PublicProjectionBundle`.

This module must run at build/deploy time, never inside a Streamlit page
render (ADR-0034 S1.2). It performs no file I/O of its own and imports
nothing beyond stdlib and this package's own dataclasses -- no
``trading_framework`` research/execution/provider import, no ML library --
so it trivially satisfies ``tests/unit/test_apps_boundaries.py``. The explicit
build-time ``publication.workspace`` helper loads catalog identities; callers
still supply already-parsed raw dicts keyed by artifact id and role here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dashboard_app.publication.errors import (
    DuplicateArtifactIdError,
    PublicationError,
    UnsafePublicIdentityError,
)
from dashboard_app.publication.identity import is_safe_artifact_id
from dashboard_app.publication.projection import (
    PUBLIC_PROJECTION_SCHEMA_VERSION,
    ProjectedArtifact,
    PublicProjectionBundle,
)
from dashboard_app.publication.sanitizers import sanitizer_for_role

#: Provenance-only identifier for the generator implementation that produced
#: a bundle. Never read for a compatibility decision (that is
#: schema_version's job) -- see PublicProjectionBundle's docstring.
GENERATOR_VERSION = "dashboard.publication.generator.v1"


@dataclass(frozen=True, slots=True)
class RawArtifactInput:
    """One not-yet-sanitized artifact to project, supplied by the caller."""

    artifact_id: str
    artifact_role: str
    raw_payload: Mapping[str, Any]


class UnknownArtifactRoleError(PublicationError):
    """A ``RawArtifactInput`` names an ``artifact_role`` with no registered sanitizer."""


def build_projection_bundle(
    raw_artifacts: list[RawArtifactInput],
    *,
    generated_at_utc: datetime,
) -> PublicProjectionBundle:
    """Sanitize every input artifact and assemble one versioned bundle.

    Raises :class:`UnknownArtifactRoleError` for an ``artifact_role`` with no
    registered sanitizer -- the generator refuses to guess, rather than
    passing an artifact through unsanitized.
    """
    artifacts: dict[str, ProjectedArtifact] = {}

    for raw_input in raw_artifacts:
        if not is_safe_artifact_id(raw_input.artifact_id):
            msg = f"unsafe public artifact_id {raw_input.artifact_id!r}"
            raise UnsafePublicIdentityError(msg)
        if raw_input.artifact_id in artifacts:
            msg = f"duplicate public artifact_id {raw_input.artifact_id!r}"
            raise DuplicateArtifactIdError(msg)
        sanitizer = sanitizer_for_role(raw_input.artifact_role)
        if sanitizer is None:
            msg = f"no sanitizer registered for artifact_role {raw_input.artifact_role!r}"
            raise UnknownArtifactRoleError(msg)

        sanitized_fields = sanitizer(raw_input.raw_payload)
        artifacts[raw_input.artifact_id] = ProjectedArtifact(
            artifact_id=raw_input.artifact_id,
            artifact_role=raw_input.artifact_role,
            fields=sanitized_fields,
        )

    return PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        generated_at_utc=generated_at_utc,
        artifacts=artifacts,
    )


def extend_projection_bundle(
    base_bundle: PublicProjectionBundle,
    raw_artifacts: list[RawArtifactInput],
    *,
    generated_at_utc: datetime,
) -> PublicProjectionBundle:
    """Add freshly sanitized artifacts to an already validated base bundle."""
    extension = build_projection_bundle(raw_artifacts, generated_at_utc=generated_at_utc)
    duplicates = set(base_bundle.artifacts).intersection(extension.artifacts)
    if duplicates:
        duplicate = sorted(duplicates)[0]
        msg = f"duplicate public artifact_id {duplicate!r} across projection bundles"
        raise DuplicateArtifactIdError(msg)
    return PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        generated_at_utc=generated_at_utc,
        artifacts={**base_bundle.artifacts, **extension.artifacts},
    )


def refresh_catalog_projection_bundle(
    base_bundle: PublicProjectionBundle,
    raw_artifacts: list[RawArtifactInput],
    *,
    generated_at_utc: datetime,
) -> PublicProjectionBundle:
    """Refresh stable catalog entries while preserving curated evidence.

    Re-running production publication against the same workspace necessarily
    rediscovers stable catalog artifact ids.  Only a catalog entry may replace
    an earlier artifact with the same id and role.  Any cross-role or curated
    artifact collision remains a fail-closed error.
    """
    from dashboard_app.publication.catalog import RESEARCH_CATALOG_ENTRY_ROLE

    extension = build_projection_bundle(raw_artifacts, generated_at_utc=generated_at_utc)
    artifacts = dict(base_bundle.artifacts)
    for artifact_id, artifact in extension.artifacts.items():
        existing = artifacts.get(artifact_id)
        if existing is not None and (
            existing.artifact_role != RESEARCH_CATALOG_ENTRY_ROLE
            or artifact.artifact_role != RESEARCH_CATALOG_ENTRY_ROLE
        ):
            msg = f"duplicate public artifact_id {artifact_id!r} across projection bundles"
            raise DuplicateArtifactIdError(msg)
        artifacts[artifact_id] = artifact
    return PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        generated_at_utc=generated_at_utc,
        artifacts=artifacts,
    )
