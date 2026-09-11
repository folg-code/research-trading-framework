"""Read-only public catalog built exclusively from the projection bundle.

The module implements ADR-0035's study-first grouping.  It never receives a
workspace root and cannot construct a filesystem path from projected data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog import RESEARCH_CATALOG_ENTRY_ROLE
from dashboard_app.publication.errors import (
    InvalidProjectionSchemaError,
    UnsafePublicIdentityError,
)
from dashboard_app.publication.manifest import PortfolioStudyManifest, StudyMaturity
from dashboard_app.publication.projection import PublicProjectionBundle
from dashboard_app.publication.sanitizers import sanitize_research_catalog_entry
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
    load_study_manifest_from_path,
    resolve_study_evidence,
)

_MISSING_DATASET_IDENTITY = "dataset-not-recorded"


@dataclass(frozen=True, slots=True)
class PublicCatalogRun:
    """One path-free, already-sanitized public research run."""

    artifact_id: str
    workflow: WorkflowKind
    run_id: str
    title: str
    created_at_utc: datetime | None
    source_dataset_ref: str | None
    evaluation_timeframe: str | None
    framework_version: str | None
    artifact_schema_version: str | None
    research_scope: str | None
    experiment_id: str | None
    time_range_start_utc: datetime | None
    time_range_end_utc: datetime | None
    verdict: str | None


@dataclass(frozen=True, slots=True)
class PublicCatalogExperiment:
    """Runs sharing one persisted experiment identity inside a study group."""

    experiment_id: str
    runs: tuple[PublicCatalogRun, ...]


@dataclass(frozen=True, slots=True)
class PublicCatalogStudy:
    """An editorial study or an explicitly labelled automatic fallback group."""

    slug: str
    title: str
    editorial: bool
    maturity: StudyMaturity | None
    workflows: tuple[WorkflowKind, ...]
    source_dataset_refs: tuple[str, ...]
    experiments: tuple[PublicCatalogExperiment, ...]

    @property
    def run_count(self) -> int:
        return sum(len(experiment.runs) for experiment in self.experiments)


@dataclass(frozen=True, slots=True)
class PublicCatalogIndex:
    """Complete public catalog and its deterministic hierarchy."""

    runs: tuple[PublicCatalogRun, ...]
    studies: tuple[PublicCatalogStudy, ...]


def build_public_catalog(
    bundle: PublicProjectionBundle,
    manifests: Sequence[PortfolioStudyManifest],
) -> PublicCatalogIndex:
    """Validate projected catalog entries and group every one exactly once."""
    runs = _projected_runs(bundle)
    studies = group_public_catalog_runs(runs, manifests)
    return PublicCatalogIndex(runs=runs, studies=studies)


def load_public_catalog_from_paths(
    bundle_path: Path,
    manifests_root: Path,
) -> PublicCatalogIndex | PublicationUnavailable:
    """Load the version-controlled public inputs without workspace fallback."""
    loaded_bundle = load_projection_bundle_from_path(bundle_path)
    if isinstance(loaded_bundle, PublicationUnavailable):
        return loaded_bundle

    manifests: list[PortfolioStudyManifest] = []
    if manifests_root.is_dir():
        for path in sorted(manifests_root.glob("*.json")):
            loaded_manifest = load_study_manifest_from_path(path)
            if isinstance(loaded_manifest, PublicationUnavailable):
                return loaded_manifest
            resolved = resolve_study_evidence(loaded_manifest, loaded_bundle)
            if isinstance(resolved, PublicationUnavailable):
                return resolved
            manifests.append(loaded_manifest)

    try:
        return build_public_catalog(loaded_bundle, manifests)
    except InvalidProjectionSchemaError as exc:
        return PublicationUnavailable(reason="catalog_invalid", detail=str(exc))


def group_public_catalog_runs(
    runs: Sequence[PublicCatalogRun],
    manifests: Sequence[PortfolioStudyManifest],
) -> tuple[PublicCatalogStudy, ...]:
    """Apply editorial manifests first, then ADR-0035's deterministic fallback."""
    runs_by_artifact = {run.artifact_id: run for run in runs}
    claimed: dict[str, str] = {}
    studies: list[PublicCatalogStudy] = []
    seen_slugs: set[str] = set()

    for manifest in manifests:
        if manifest.slug in seen_slugs:
            raise InvalidProjectionSchemaError(
                f"duplicate public study manifest slug {manifest.slug!r}"
            )
        seen_slugs.add(manifest.slug)
        referenced_ids = tuple(
            dict.fromkeys(
                artifact_id
                for artifact_id in manifest.artifact_roles.values()
                if artifact_id in runs_by_artifact
            )
        )
        if not referenced_ids:
            continue
        for artifact_id in referenced_ids:
            previous = claimed.get(artifact_id)
            if previous is not None:
                raise InvalidProjectionSchemaError(
                    f"catalog artifact {artifact_id!r} is claimed by studies "
                    f"{previous!r} and {manifest.slug!r}"
                )
            claimed[artifact_id] = manifest.slug
        study_runs = tuple(runs_by_artifact[item] for item in referenced_ids)
        studies.append(
            _study(
                slug=manifest.slug,
                title=manifest.title,
                editorial=True,
                maturity=manifest.maturity,
                runs=study_runs,
            )
        )

    fallback_groups: dict[tuple[WorkflowKind, str], list[PublicCatalogRun]] = {}
    for run in runs:
        if run.artifact_id in claimed:
            continue
        dataset_identity = run.source_dataset_ref or _MISSING_DATASET_IDENTITY
        fallback_groups.setdefault((run.workflow, dataset_identity), []).append(run)

    for (workflow, dataset_identity), grouped_runs in sorted(
        fallback_groups.items(), key=lambda item: (item[0][0].value, item[0][1])
    ):
        canonical = f"{workflow.value}\n{dataset_identity}"
        digest = sha256(canonical.encode("utf-8")).hexdigest()[:12]
        dataset_title = (
            "Dataset not recorded"
            if dataset_identity == _MISSING_DATASET_IDENTITY
            else dataset_identity
        )
        studies.append(
            _study(
                slug=f"auto-{workflow.value}-{digest}",
                title=f"{workflow.value.title()} · {dataset_title}",
                editorial=False,
                maturity=None,
                runs=tuple(grouped_runs),
            )
        )

    return tuple(studies)


def select_public_catalog_studies(
    studies: Sequence[PublicCatalogStudy],
    runs: Sequence[PublicCatalogRun],
) -> tuple[PublicCatalogStudy, ...]:
    """Preserve study membership while retaining only selected public runs."""
    selected_ids = {run.artifact_id for run in runs}
    selected_studies: list[PublicCatalogStudy] = []
    for study in studies:
        experiments = tuple(
            replace(
                experiment,
                runs=tuple(run for run in experiment.runs if run.artifact_id in selected_ids),
            )
            for experiment in study.experiments
            if any(run.artifact_id in selected_ids for run in experiment.runs)
        )
        if experiments:
            selected_studies.append(replace(study, experiments=experiments))
    return tuple(selected_studies)


def _projected_runs(bundle: PublicProjectionBundle) -> tuple[PublicCatalogRun, ...]:
    runs: list[PublicCatalogRun] = []
    for artifact in bundle.artifacts.values():
        if artifact.artifact_role != RESEARCH_CATALOG_ENTRY_ROLE:
            continue
        raw_fields = dict(artifact.fields)
        try:
            sanitized = sanitize_research_catalog_entry(raw_fields)
        except UnsafePublicIdentityError as exc:
            raise InvalidProjectionSchemaError(
                f"invalid catalog artifact {artifact.artifact_id!r}: {exc}"
            ) from exc
        if sanitized != raw_fields:
            raise InvalidProjectionSchemaError(
                f"catalog artifact {artifact.artifact_id!r} contains non-allowlisted fields"
            )
        try:
            workflow = WorkflowKind(str(sanitized["workflow"]))
            runs.append(
                PublicCatalogRun(
                    artifact_id=artifact.artifact_id,
                    workflow=workflow,
                    run_id=str(sanitized["run_id"]),
                    title=str(sanitized["title"]),
                    created_at_utc=_timestamp(sanitized, "created_at_utc"),
                    source_dataset_ref=_optional_text(sanitized, "source_dataset_ref"),
                    evaluation_timeframe=_optional_text(sanitized, "evaluation_timeframe"),
                    framework_version=_optional_text(sanitized, "framework_version"),
                    artifact_schema_version=_optional_text(sanitized, "artifact_schema_version"),
                    research_scope=_optional_text(sanitized, "research_scope"),
                    experiment_id=_optional_text(sanitized, "experiment_id"),
                    time_range_start_utc=_timestamp(sanitized, "time_range_start_utc"),
                    time_range_end_utc=_timestamp(sanitized, "time_range_end_utc"),
                    verdict=_optional_text(sanitized, "verdict"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidProjectionSchemaError(
                f"malformed catalog artifact {artifact.artifact_id!r}: {exc}"
            ) from exc

    runs.sort(key=_run_sort_key, reverse=True)
    return tuple(runs)


def _study(
    *,
    slug: str,
    title: str,
    editorial: bool,
    maturity: StudyMaturity | None,
    runs: Sequence[PublicCatalogRun],
) -> PublicCatalogStudy:
    experiments: dict[str, list[PublicCatalogRun]] = {}
    for run in runs:
        experiments.setdefault(run.experiment_id or run.run_id, []).append(run)
    grouped_experiments = tuple(
        PublicCatalogExperiment(
            experiment_id=experiment_id,
            runs=tuple(sorted(items, key=_run_sort_key, reverse=True)),
        )
        for experiment_id, items in sorted(experiments.items())
    )
    workflows = tuple(sorted({run.workflow for run in runs}, key=lambda item: item.value))
    datasets = tuple(sorted({run.source_dataset_ref or _MISSING_DATASET_IDENTITY for run in runs}))
    return PublicCatalogStudy(
        slug=slug,
        title=title,
        editorial=editorial,
        maturity=maturity,
        workflows=workflows,
        source_dataset_refs=datasets,
        experiments=grouped_experiments,
    )


def _run_sort_key(run: PublicCatalogRun) -> tuple[str, str]:
    created = run.created_at_utc.isoformat() if run.created_at_utc is not None else ""
    return created, run.run_id


def _timestamp(fields: Mapping[str, object], key: str) -> datetime | None:
    value = fields.get(key)
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.utcoffset() is None:
        raise ValueError(f"{key} must be timezone-aware")
    return parsed


def _optional_text(fields: Mapping[str, object], key: str) -> str | None:
    value = fields.get(key)
    return str(value) if value is not None else None
