"""Public portfolio publication boundary (ADR-0034, Sprint 059 T002).

The only path a new public portfolio page may use to read research facts: a
pre-generated, deny-by-default
:class:`~dashboard_app.publication.projection.PublicProjectionBundle` grouped
into named studies by a
:class:`~dashboard_app.publication.manifest.PortfolioStudyManifest`. Nothing
in this package scans the private workspace or builds a filesystem path from
a projected value.
"""

from __future__ import annotations

from dashboard_app.publication.errors import (
    InvalidProjectionSchemaError,
    PublicationError,
)
from dashboard_app.publication.generator import (
    GENERATOR_VERSION,
    RawArtifactInput,
    UnknownArtifactRoleError,
    build_projection_bundle,
)
from dashboard_app.publication.manifest import (
    PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
    PortfolioStudyManifest,
    StudyMaturity,
)
from dashboard_app.publication.paths import (
    PUBLICATION_DATA_ROOT,
    projection_bundle_path,
    study_manifest_path,
)
from dashboard_app.publication.projection import (
    PUBLIC_PROJECTION_SCHEMA_VERSION,
    ProjectedArtifact,
    PublicProjectionBundle,
)
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    StudyEvidence,
    load_projection_bundle,
    load_projection_bundle_from_path,
    load_study_manifest,
    load_study_manifest_from_path,
    resolve_study_evidence,
)

__all__ = [
    "GENERATOR_VERSION",
    "PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION",
    "PUBLICATION_DATA_ROOT",
    "PUBLIC_PROJECTION_SCHEMA_VERSION",
    "InvalidProjectionSchemaError",
    "PortfolioStudyManifest",
    "ProjectedArtifact",
    "PublicProjectionBundle",
    "PublicationError",
    "PublicationUnavailable",
    "RawArtifactInput",
    "StudyEvidence",
    "StudyMaturity",
    "UnknownArtifactRoleError",
    "build_projection_bundle",
    "load_projection_bundle",
    "load_projection_bundle_from_path",
    "load_study_manifest",
    "load_study_manifest_from_path",
    "projection_bundle_path",
    "resolve_study_evidence",
    "study_manifest_path",
]
