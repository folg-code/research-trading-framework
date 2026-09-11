"""Build-time discovery of safely publishable research catalog entries.

This is the only publication helper that reads the private workspace. Public
Streamlit pages must consume the generated bundle and must never call this
module at request time.
"""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_app.catalog.scanner import list_runs
from dashboard_app.contracts import RunSummary
from dashboard_app.publication.catalog import build_catalog_artifact_input
from dashboard_app.publication.errors import UnsafePublicIdentityError
from dashboard_app.publication.generator import RawArtifactInput


def discover_catalog_inputs(storage_root: Path) -> tuple[list[RawArtifactInput], int]:
    """Return safe catalog inputs and the number of skipped unsafe/corrupt runs."""
    catalog = list_runs(storage_root)
    inputs: list[RawArtifactInput] = []
    skipped = len(catalog.issues)
    for summary in catalog.runs:
        try:
            inputs.append(
                build_catalog_artifact_input(
                    summary,
                    verdict=_load_persisted_verdict(summary),
                )
            )
        except UnsafePublicIdentityError:
            skipped += 1
    return inputs, skipped


def _load_persisted_verdict(summary: RunSummary) -> str | None:
    path = Path(summary.storage_path) / "verdict.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    verdict = payload.get("verdict")
    return str(verdict) if verdict is not None else None
