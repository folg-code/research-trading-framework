"""Production publication release and deployment-boundary tests (S061-T007)."""

from __future__ import annotations

import os
import stat
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


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits only")
def test_prepare_release_is_world_readable_for_a_different_container_user(tmp_path: Path) -> None:
    """The deploy generator and the long-running dashboard container run as
    different, unrelated users (build-time generator vs. the container's own
    ``dashboard`` system user; see ``deploy_public_dashboard.sh``), sharing
    the release tree only through a plain bind mount -- no common group.
    ``tempfile.mkdtemp``/``mkstemp`` always create 0700/0600 regardless of
    umask, which would otherwise make every release unreadable by anyone but
    the user that generated it. Every directory/file in the release tree
    must be world-readable (files) / world-traversable (directories).
    """
    storage_root = tmp_path / "workspace"
    storage_root.mkdir()
    release_root = tmp_path / "publication"

    release = prepare_public_projection_release(
        storage_root=storage_root,
        release_root=release_root,
        release_id="release-perm-001",
        base_bundle_path=projection_bundle_path(),
        generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
    )

    def other_can_read(path: Path) -> bool:
        return bool(path.stat().st_mode & stat.S_IROTH)

    def other_can_traverse(path: Path) -> bool:
        return bool(path.stat().st_mode & stat.S_IXOTH)

    release_directory = release.projection_path.parent
    assert other_can_traverse(release_root)
    assert other_can_traverse(release_root / "releases")
    assert other_can_traverse(release_directory)
    assert other_can_read(release.projection_path)
    manifests_directory = release_directory / "manifests"
    assert other_can_traverse(manifests_directory)
    for manifest_path in manifests_directory.iterdir():
        assert other_can_read(manifest_path)
    assert other_can_read(release_root / "CURRENT")


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
    assert "dst=/research,readonly" in deploy_script
    assert "--evidence-root /research" in deploy_script
    assert "dashboard_app.publication.release" in deploy_script
    assert "deploy_public_dashboard.sh" in workflow
    assert workflow.index("git reset --hard origin/main") < workflow.index(
        "deploy_public_dashboard.sh"
    )
