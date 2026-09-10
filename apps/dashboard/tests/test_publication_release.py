"""Production publication release and deployment-boundary tests (S061-T007)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard_app.publication.paths import projection_bundle_path
from dashboard_app.publication.release import (
    prepare_public_projection_release,
    resolve_selected_projection,
)
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_prepare_release_validates_before_updating_current(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    storage_root.mkdir()
    release_root = tmp_path / "publication"

    release = prepare_public_projection_release(
        storage_root=storage_root,
        release_root=release_root,
        release_id="release-001",
        base_bundle_path=projection_bundle_path(),
        generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
    )

    assert (release_root / "CURRENT").read_text(encoding="utf-8") == "release-001\n"
    assert release.projection_path == resolve_selected_projection(release_root)
    assert (release_root / "releases/release-001/manifests/btc-signal-quality.json").is_file()
    loaded = load_projection_bundle_from_path(release.projection_path)
    assert not isinstance(loaded, PublicationUnavailable)
    assert release.artifact_count == len(loaded.artifacts)


def test_failed_generation_preserves_previous_selection(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    storage_root.mkdir()
    release_root = tmp_path / "publication"
    release_root.mkdir()
    (release_root / "CURRENT").write_text("known-good\n", encoding="utf-8")

    with pytest.raises(ValueError, match="base projection unavailable"):
        prepare_public_projection_release(
            storage_root=storage_root,
            release_root=release_root,
            release_id="release-002",
            base_bundle_path=tmp_path / "missing.json",
        )

    assert (release_root / "CURRENT").read_text(encoding="utf-8") == "known-good\n"
    assert not (release_root / "releases" / "release-002").exists()


def test_manifest_validation_failure_preserves_previous_selection(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    storage_root.mkdir()
    release_root = tmp_path / "publication"
    release_root.mkdir()
    (release_root / "CURRENT").write_text("known-good\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no study manifests found"):
        prepare_public_projection_release(
            storage_root=storage_root,
            release_root=release_root,
            release_id="release-003",
            base_bundle_path=projection_bundle_path(),
            manifests_root=tmp_path / "missing-manifests",
        )

    assert (release_root / "CURRENT").read_text(encoding="utf-8") == "known-good\n"
    assert not (release_root / "releases" / "release-003").exists()


@pytest.mark.parametrize("release_id", ["../escape", "slash/value", "", "with spaces"])
def test_release_id_rejects_path_syntax(tmp_path: Path, release_id: str) -> None:
    with pytest.raises(ValueError, match="unsafe public projection release id"):
        prepare_public_projection_release(
            storage_root=tmp_path,
            release_root=tmp_path / "publication",
            release_id=release_id,
            base_bundle_path=projection_bundle_path(),
        )


def test_deployed_dashboard_mounts_only_selected_projection() -> None:
    compose = (_REPO_ROOT / "apps/dashboard/deploy/docker-compose.yml").read_text(encoding="utf-8")
    deploy_script = (_REPO_ROOT / "scripts/dashboard/deploy_public_dashboard.sh").read_text(
        encoding="utf-8"
    )
    workflow = (_REPO_ROOT / ".github/workflows/deploy-dashboard.yml").read_text(encoding="utf-8")

    assert "DASHBOARD_PUBLICATION_HOST_PATH" in compose
    assert "target: /opt/dashboard/publication_data" in compose
    assert "DASHBOARD_STORAGE_HOST_PATH" not in compose
    assert "dst=/workspace,readonly" in deploy_script
    assert "dashboard_app.publication.release" in deploy_script
    assert "deploy_public_dashboard.sh" in workflow
    assert workflow.index("git reset --hard origin/main") < workflow.index(
        "deploy_public_dashboard.sh"
    )
