"""Prepare and atomically select immutable public projection releases.

This module is a build/deploy-time entry point.  The public Streamlit process
never imports it and never receives the private workspace mount.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dashboard_app.publication.evidence import discover_research_evidence_inputs
from dashboard_app.publication.generator import (
    RawArtifactInput,
    refresh_publication_projection_bundle,
)
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.projection import PublicProjectionBundle
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.publication.workspace import discover_catalog_inputs

_SAFE_RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CURRENT_RELEASE_FILE = "CURRENT"
RELEASES_DIRECTORY = "releases"

# The release tree is deliberately public data (a sanitized projection bundle
# meant to be read by the long-running dashboard container), but the build-time
# generator and the dashboard process run as different, unrelated host/container
# users -- there is no shared group to rely on. `tempfile.mkdtemp`/`mkstemp`
# always create with 0700/0600 regardless of umask (a private-by-default
# security choice in CPython's tempfile module), which would otherwise leave
# every release unreadable by anyone but the user that generated it. Every
# directory/file in the release tree is explicitly widened after creation so
# the released data matches its actual (public) sensitivity, not the
# generator's private-temp-file default.
_PUBLIC_DIR_MODE = 0o755
_PUBLIC_FILE_MODE = 0o644


@dataclass(frozen=True, slots=True)
class ProjectionRelease:
    """A validated immutable release selected for deployment."""

    release_id: str
    projection_path: Path
    artifact_count: int
    discovered_count: int
    skipped_count: int


def prepare_public_projection_release(
    *,
    storage_root: Path,
    release_root: Path,
    release_id: str,
    base_bundle_path: Path,
    evidence_root: Path | None = None,
    manifests_root: Path = STUDY_MANIFESTS_ROOT,
    generated_at_utc: datetime | None = None,
) -> ProjectionRelease:
    """Generate, validate, persist and then atomically select one release.

    A release id is never overwritten.  ``CURRENT`` changes only after the
    candidate bundle has passed the same schema validation used by readers.
    Therefore any generation or validation failure leaves the previous
    selection untouched.
    """
    _validate_release_id(release_id)
    release_root = release_root.resolve()
    releases_root = release_root / RELEASES_DIRECTORY
    final_directory = releases_root / release_id
    if final_directory.exists():
        raise ValueError(f"projection release already exists: {release_id}")

    base_bundle = _load_bundle(base_bundle_path, label="base")
    raw_inputs, skipped_count = discover_catalog_inputs(storage_root)
    generated_at = generated_at_utc or datetime.now(UTC)
    evidence_inputs: list[RawArtifactInput] = []
    evidence_skipped = 0
    if evidence_root is not None:
        evidence_inputs, evidence_skipped = discover_research_evidence_inputs(evidence_root)
    bundle = refresh_publication_projection_bundle(
        base_bundle,
        [*raw_inputs, *evidence_inputs],
        generated_at_utc=generated_at,
    )

    releases_root.mkdir(parents=True, exist_ok=True)
    releases_root.chmod(_PUBLIC_DIR_MODE)
    candidate_directory = Path(tempfile.mkdtemp(prefix=f".{release_id}.", dir=releases_root))
    try:
        candidate_path = candidate_directory / "projection.json"
        _write_bundle(candidate_path, bundle)
        candidate_path.chmod(_PUBLIC_FILE_MODE)
        validated = _load_bundle(candidate_path, label="generated")
        manifest_paths = _validate_manifests(manifests_root, validated)
        release_manifests = candidate_directory / "manifests"
        release_manifests.mkdir()
        release_manifests.chmod(_PUBLIC_DIR_MODE)
        for manifest_path in manifest_paths:
            copied_path = release_manifests / manifest_path.name
            shutil.copy2(manifest_path, copied_path)
            copied_path.chmod(_PUBLIC_FILE_MODE)
        # mkdtemp always creates 0700 regardless of umask; widen the directory
        # itself last, once its contents are already public-mode, so there is
        # no window where a public-mode file sits inside a private directory.
        candidate_directory.chmod(_PUBLIC_DIR_MODE)
        os.replace(candidate_directory, final_directory)
    except Exception:
        shutil.rmtree(candidate_directory, ignore_errors=True)
        raise

    _select_release(release_root, release_id)
    return ProjectionRelease(
        release_id=release_id,
        projection_path=final_directory / "projection.json",
        artifact_count=len(validated.artifacts),
        discovered_count=len(raw_inputs) + len(evidence_inputs),
        skipped_count=skipped_count + evidence_skipped,
    )


def resolve_selected_projection(release_root: Path) -> Path:
    """Resolve and validate the projection named by the atomic pointer."""
    current_path = release_root / CURRENT_RELEASE_FILE
    try:
        release_id = current_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"public projection selection unavailable: {exc}") from exc
    _validate_release_id(release_id)
    selected = release_root / RELEASES_DIRECTORY / release_id / "projection.json"
    _load_bundle(selected, label="selected")
    return selected


def _validate_release_id(release_id: str) -> None:
    if _SAFE_RELEASE_ID.fullmatch(release_id) is None:
        raise ValueError(f"unsafe public projection release id: {release_id!r}")


def _load_bundle(path: Path, *, label: str) -> PublicProjectionBundle:
    result = load_projection_bundle_from_path(path)
    if isinstance(result, PublicationUnavailable):
        raise ValueError(f"{label} projection unavailable: {result.reason}: {result.detail}")
    return result


def _write_bundle(path: Path, bundle: PublicProjectionBundle) -> None:
    path.write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _validate_manifests(manifests_root: Path, bundle: PublicProjectionBundle) -> list[Path]:
    from dashboard_app.publication.validation import (
        load_study_manifest_from_path,
        resolve_study_evidence,
    )

    manifest_paths = sorted(manifests_root.glob("*.json"))
    if not manifest_paths:
        raise ValueError(f"no study manifests found: {manifests_root}")
    for manifest_path in manifest_paths:
        manifest = load_study_manifest_from_path(manifest_path)
        if isinstance(manifest, PublicationUnavailable):
            raise ValueError(f"study manifest unavailable: {manifest.reason}: {manifest.detail}")
        evidence = resolve_study_evidence(manifest, bundle)
        if isinstance(evidence, PublicationUnavailable):
            raise ValueError(f"study manifest unresolved: {evidence.reason}: {evidence.detail}")
    return manifest_paths


def _select_release(release_root: Path, release_id: str) -> None:
    release_root.mkdir(parents=True, exist_ok=True)
    release_root.chmod(_PUBLIC_DIR_MODE)
    handle, temporary_name = tempfile.mkstemp(prefix=".CURRENT.", dir=release_root, text=True)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(f"{release_id}\n")
        # mkstemp always creates 0600 regardless of umask.
        temporary_path.chmod(_PUBLIC_FILE_MODE)
        os.replace(temporary_path, release_root / CURRENT_RELEASE_FILE)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        help="Private research root for projected Signal/Robustness analytics.",
    )
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--base-bundle", type=Path, default=projection_bundle_path())
    parser.add_argument("--manifests-root", type=Path, default=STUDY_MANIFESTS_ROOT)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    release = prepare_public_projection_release(
        storage_root=args.storage_root,
        release_root=args.release_root,
        release_id=args.release_id,
        base_bundle_path=args.base_bundle,
        evidence_root=args.evidence_root,
        manifests_root=args.manifests_root,
    )
    print(
        f"selected {release.release_id}: {release.artifact_count} artifacts "
        f"({release.discovered_count} discovered, {release.skipped_count} skipped)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
