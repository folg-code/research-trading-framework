"""Portfolio study identity (ADR-0034 S2).

``PortfolioStudyManifest`` is a dashboard-local, version-controlled
presentation contract. It groups projected artifacts into a named study
without claiming any cross-workflow lineage the persisted artifacts do not
evidence -- see ADR-0034 S2.3. No framework study aggregate, no persisted
index, no ``latest`` pointer is introduced here (ADR-0024 condition 5).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from dashboard_app.contracts import WorkflowKind

#: No minor-version scheme yet; see projection.py's schema_version note.
PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION = "dashboard.study_manifest.v1"


class StudyMaturity(StrEnum):
    """Wire/schema values for a study's maturity label.

    These are the schema values, not display text: SPRINT_059.md's Scope
    section uses the space-containing display strings "AS BUILT",
    "IN DEVELOPMENT", "FUTURE IDEAS", "ARCHIVED" -- rendering that mapping is
    a view-layer concern (Sprint 059 T005), not this contract's job.
    """

    AS_BUILT = "AS_BUILT"
    IN_DEVELOPMENT = "IN_DEVELOPMENT"
    FUTURE_IDEAS = "FUTURE_IDEAS"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class PortfolioStudyManifest:
    """One named study grouping projected artifacts by explicit role.

    ``artifact_roles`` maps one role name to exactly one ``artifact_id``
    (ADR-0034 S2.2) -- never a list, never an inferred pipeline. Role-name
    strings are deliberately not a closed enum: freezing the vocabulary now
    would contradict "role vocabulary additive" (ADR-0034 S2.5) and would
    force this task to guess Sprint 060's role names. Structural validation
    (non-empty role names, dangling-reference detection) lives in
    :mod:`dashboard_app.publication.validation`, not here.
    """

    schema_version: str
    slug: str
    title: str
    maturity: StudyMaturity
    workflows: tuple[WorkflowKind, ...]
    artifact_roles: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_roles", MappingProxyType(dict(self.artifact_roles)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "slug": self.slug,
            "title": self.title,
            "maturity": self.maturity.value,
            "workflows": [workflow.value for workflow in self.workflows],
            "artifact_roles": dict(self.artifact_roles),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PortfolioStudyManifest:
        return cls(
            schema_version=str(payload["schema_version"]),
            slug=str(payload["slug"]),
            title=str(payload["title"]),
            maturity=StudyMaturity(str(payload["maturity"])),
            workflows=tuple(WorkflowKind(str(item)) for item in payload.get("workflows", [])),
            artifact_roles={
                str(role): str(artifact_id)
                for role, artifact_id in payload.get("artifact_roles", {}).items()
            },
        )
