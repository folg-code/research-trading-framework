"""Public projection bundle (ADR-0034 S1).

The single input the new public portfolio path may read. Generated at
build/deploy time by :mod:`dashboard_app.publication.generator`, never by a
Streamlit page at request time. Every payload inside an artifact's
``fields`` has already passed a deny-by-default allowlist
(:mod:`dashboard_app.publication.sanitizers`) -- this module never inspects
or filters field content itself, only the envelope shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from dashboard_app.publication.errors import InvalidProjectionSchemaError

#: The one schema version this module produces and accepts. There is no
#: minor-version scheme yet (ADR-0034 S5: additive changes within a major
#: version do not require a new string); a payload whose ``schema_version``
#: does not match exactly is refused rather than guessed at.
PUBLIC_PROJECTION_SCHEMA_VERSION = "dashboard.public.v1"


@dataclass(frozen=True, slots=True)
class ProjectedArtifact:
    """One sanitized, publicly-projectable artifact.

    ``artifact_id`` is a projection-local identifier -- never a filesystem
    path and never derived from one (ADR-0034 S1.5). ``fields`` is the
    already-sanitized payload for this artifact's role; this class does not
    itself enforce the allowlist, only carries the result of one.
    """

    artifact_id: str
    artifact_role: str
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_role": self.artifact_role,
            "fields": dict(self.fields),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProjectedArtifact:
        return cls(
            artifact_id=str(payload["artifact_id"]),
            artifact_role=str(payload["artifact_role"]),
            fields=dict(payload.get("fields", {})),
        )


@dataclass(frozen=True, slots=True)
class PublicProjectionBundle:
    """The versioned envelope the public portfolio path reads exclusively.

    ``generator_version`` is provenance only (which generator build produced
    this bundle) and is never read for a compatibility decision --
    ``schema_version`` alone governs whether a consumer may render this
    bundle (ADR-0034 S5).
    """

    schema_version: str
    generator_version: str
    generated_at_utc: datetime
    artifacts: Mapping[str, ProjectedArtifact]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", MappingProxyType(dict(self.artifacts)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "generated_at_utc": self.generated_at_utc.isoformat(),
            "artifacts": {
                artifact_id: artifact.to_dict() for artifact_id, artifact in self.artifacts.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PublicProjectionBundle:
        schema_version = payload.get("schema_version")
        if schema_version != PUBLIC_PROJECTION_SCHEMA_VERSION:
            msg = (
                f"unsupported public projection schema_version: {schema_version!r} "
                f"(expected {PUBLIC_PROJECTION_SCHEMA_VERSION!r})"
            )
            raise InvalidProjectionSchemaError(msg)

        try:
            generated_at_utc = datetime.fromisoformat(str(payload["generated_at_utc"]))
            artifacts_payload = payload["artifacts"]
            generator_version = str(payload["generator_version"])
        except (KeyError, ValueError) as exc:
            msg = f"malformed public projection bundle payload: {exc}"
            raise InvalidProjectionSchemaError(msg) from exc

        if not isinstance(artifacts_payload, Mapping):
            msg = "public projection bundle 'artifacts' must be a mapping"
            raise InvalidProjectionSchemaError(msg)

        try:
            artifacts = {
                artifact_id: ProjectedArtifact.from_dict(artifact_payload)
                for artifact_id, artifact_payload in artifacts_payload.items()
            }
        except (KeyError, TypeError, AttributeError) as exc:
            msg = f"malformed artifact entry in public projection bundle: {exc}"
            raise InvalidProjectionSchemaError(msg) from exc

        return cls(
            schema_version=schema_version,
            generator_version=generator_version,
            generated_at_utc=generated_at_utc,
            artifacts=artifacts,
        )
