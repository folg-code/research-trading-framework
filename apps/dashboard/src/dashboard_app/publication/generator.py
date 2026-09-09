"""Public projection generator (ADR-0034 S1.2).

Orchestration only: given already-loaded raw artifact payloads, look up the
matching sanitizer by role, wrap each sanitized result in a
:class:`~dashboard_app.publication.projection.ProjectedArtifact`, and
assemble a :class:`~dashboard_app.publication.projection.PublicProjectionBundle`.

This module must run at build/deploy time, never inside a Streamlit page
render (ADR-0034 S1.2). It performs no file I/O of its own and imports
nothing beyond stdlib and this package's own dataclasses -- no
``trading_framework`` research/execution/provider import, no ML library --
so it trivially satisfies ``tests/unit/test_apps_boundaries.py``. Loading
real raw artifacts off disk and the full Sprint 060 field inventory are
explicitly out of scope for this generator today; a caller supplies
already-parsed raw dicts keyed by artifact_id and role.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dashboard_app.publication.errors import PublicationError
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
