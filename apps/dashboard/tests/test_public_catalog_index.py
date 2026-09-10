"""Sprint 061 T006 tests for the projection-backed public catalog."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog import RESEARCH_CATALOG_ENTRY_ROLE
from dashboard_app.publication.catalog_index import (
    PublicCatalogIndex,
    build_public_catalog,
    load_public_catalog_from_paths,
    select_public_catalog_studies,
)
from dashboard_app.publication.errors import InvalidProjectionSchemaError
from dashboard_app.publication.manifest import (
    PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
    PortfolioStudyManifest,
    StudyMaturity,
)
from dashboard_app.publication.projection import (
    PUBLIC_PROJECTION_SCHEMA_VERSION,
    ProjectedArtifact,
    PublicProjectionBundle,
)
from dashboard_app.publication.validation import PublicationUnavailable


def _artifact(
    run_id: str,
    *,
    workflow: str = "predictive",
    dataset: str | None = "BTCUSDT.P|ohlcv|1m|binance|klines@1",
    experiment_id: str | None = "experiment-1",
    verdict: str | None = None,
) -> ProjectedArtifact:
    fields: dict[str, object] = {
        "workflow": workflow,
        "run_id": run_id,
        "title": f"{workflow.title()} · model-{run_id}",
        "created_at_utc": "2026-09-10T10:00:00+00:00",
        "evaluation_timeframe": "1m",
        "time_range_start_utc": "2024-01-01T00:00:00+00:00",
        "time_range_end_utc": "2024-06-30T00:00:00+00:00",
    }
    if dataset is not None:
        fields["source_dataset_ref"] = dataset
    if experiment_id is not None:
        fields["experiment_id"] = experiment_id
    if verdict is not None:
        fields["verdict"] = verdict
    return ProjectedArtifact(
        artifact_id=f"catalog-{workflow}-{run_id}",
        artifact_role=RESEARCH_CATALOG_ENTRY_ROLE,
        fields=fields,
    )


def _bundle(*artifacts: ProjectedArtifact) -> PublicProjectionBundle:
    return PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version="test",
        generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        artifacts={artifact.artifact_id: artifact for artifact in artifacts},
    )


def _manifest(*artifact_ids: str, slug: str = "curated-study") -> PortfolioStudyManifest:
    return PortfolioStudyManifest(
        schema_version=PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
        slug=slug,
        title="Curated Study",
        maturity=StudyMaturity.AS_BUILT,
        workflows=(WorkflowKind.PREDICTIVE, WorkflowKind.STRATEGY),
        artifact_roles={f"catalog_{index}": value for index, value in enumerate(artifact_ids)},
    )


def test_catalog_groups_manifest_members_first_and_every_other_run_automatically() -> None:
    curated = _artifact("curated", verdict="INCONCLUSIVE")
    automatic_a = _artifact("auto-a")
    automatic_b = _artifact("auto-b")

    catalog = build_public_catalog(
        _bundle(curated, automatic_a, automatic_b),
        [_manifest(curated.artifact_id)],
    )

    assert catalog.studies[0].slug == "curated-study"
    assert catalog.studies[0].editorial is True
    assert catalog.studies[0].run_count == 1
    automatic = catalog.studies[1]
    assert automatic.editorial is False
    assert automatic.slug.startswith("auto-predictive-")
    assert automatic.run_count == 2
    assert [item.experiment_id for item in automatic.experiments] == ["experiment-1"]
    assert [run.run_id for run in automatic.experiments[0].runs] == ["auto-b", "auto-a"]


def test_fallback_uses_run_id_when_experiment_and_dataset_are_missing() -> None:
    run = _artifact("standalone", dataset=None, experiment_id=None)

    catalog = build_public_catalog(_bundle(run), [])

    study = catalog.studies[0]
    assert study.source_dataset_refs == ("dataset-not-recorded",)
    assert study.experiments[0].experiment_id == "standalone"


def test_missing_verdict_remains_no_value_in_read_model() -> None:
    catalog = build_public_catalog(_bundle(_artifact("no-verdict")), [])

    assert catalog.runs[0].verdict is None


def test_catalog_rejects_non_allowlisted_projected_field() -> None:
    artifact = _artifact("unsafe")
    artifact = ProjectedArtifact(
        artifact_id=artifact.artifact_id,
        artifact_role=artifact.artifact_role,
        fields={**artifact.fields, "storage_path": "C:/private/workspace"},
    )

    with pytest.raises(InvalidProjectionSchemaError, match="non-allowlisted"):
        build_public_catalog(_bundle(artifact), [])


def test_catalog_rejects_one_run_claimed_by_two_studies() -> None:
    artifact = _artifact("shared")

    with pytest.raises(InvalidProjectionSchemaError, match="claimed by studies"):
        build_public_catalog(
            _bundle(artifact),
            [
                _manifest(artifact.artifact_id, slug="one"),
                _manifest(artifact.artifact_id, slug="two"),
            ],
        )


def test_filtered_hierarchy_preserves_original_study_membership() -> None:
    first = _artifact("first")
    second = _artifact("second")
    catalog = build_public_catalog(_bundle(first, second), [_manifest(first.artifact_id)])

    selected_run = next(run for run in catalog.runs if run.artifact_id == second.artifact_id)
    selected = select_public_catalog_studies(catalog.studies, [selected_run])

    assert len(selected) == 1
    assert selected[0].editorial is False
    assert selected[0].run_count == 1


def test_path_loader_fails_closed_for_invalid_catalog_entry(tmp_path: Path) -> None:
    artifact = _artifact("bad")
    payload = _bundle(artifact).to_dict()
    payload["artifacts"][artifact.artifact_id]["fields"]["unknown"] = "must-not-pass"
    bundle_path = tmp_path / "projection.json"
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")

    result = load_public_catalog_from_paths(bundle_path, tmp_path / "manifests")

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "catalog_invalid"


def test_path_loader_fails_closed_for_dangling_study_reference(tmp_path: Path) -> None:
    artifact = _artifact("valid")
    bundle_path = tmp_path / "projection.json"
    bundle_path.write_text(json.dumps(_bundle(artifact).to_dict()), encoding="utf-8")
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "broken.json").write_text(
        json.dumps(_manifest("catalog-predictive-missing").to_dict()),
        encoding="utf-8",
    )

    result = load_public_catalog_from_paths(bundle_path, manifests)

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "dangling_reference"


def test_committed_publication_contains_grouped_path_free_catalog() -> None:
    root = Path(__file__).resolve().parents[1] / "publication_data"

    result = load_public_catalog_from_paths(root / "projection.json", root / "manifests")

    assert isinstance(result, PublicCatalogIndex)
    assert len(result.runs) == 7
    assert any(study.editorial for study in result.studies)
    assert any(not study.editorial for study in result.studies)
    assert "storage_path" not in repr(result)
