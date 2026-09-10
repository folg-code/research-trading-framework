"""Public portfolio publication boundary (ADR-0034, Sprint 059 T002).

The only path a new public portfolio page may use to read research facts: a
pre-generated, deny-by-default
:class:`~dashboard_app.publication.projection.PublicProjectionBundle` grouped
into named studies by a
:class:`~dashboard_app.publication.manifest.PortfolioStudyManifest`. Public
pages never scan the private workspace or build a filesystem path from a
projected value. The explicit ``publication.workspace`` build-time helper is
the sole exception and only produces sanitizer inputs before deployment.
"""

from __future__ import annotations

from dashboard_app.publication.catalog import (
    RESEARCH_CATALOG_ENTRY_ROLE,
    build_catalog_artifact_input,
    catalog_artifact_id,
)
from dashboard_app.publication.errors import (
    DuplicateArtifactIdError,
    InvalidProjectionSchemaError,
    PublicationError,
    UnsafePublicIdentityError,
)
from dashboard_app.publication.generator import (
    GENERATOR_VERSION,
    RawArtifactInput,
    UnknownArtifactRoleError,
    build_projection_bundle,
    extend_projection_bundle,
)
from dashboard_app.publication.identity import is_safe_artifact_id
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
    "RESEARCH_CATALOG_ENTRY_ROLE",
    "DuplicateArtifactIdError",
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
    "UnsafePublicIdentityError",
    "build_catalog_artifact_input",
    "build_projection_bundle",
    "catalog_artifact_id",
    "extend_projection_bundle",
    "is_safe_artifact_id",
    "load_projection_bundle",
    "load_projection_bundle_from_path",
    "load_study_manifest",
    "load_study_manifest_from_path",
    "projection_bundle_path",
    "resolve_study_evidence",
    "study_manifest_path",
]
