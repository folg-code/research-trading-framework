"""Safe public-catalog inputs for the build-time projection generator.

This module converts dashboard-local ``RunSummary`` values into one explicit,
deny-by-default projection role. It never scans storage itself and never copies
``storage_path``. Filesystem discovery remains a build-time caller concern.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.publication.errors import UnsafePublicIdentityError
from dashboard_app.publication.generator import RawArtifactInput
from dashboard_app.publication.identity import (
    is_safe_artifact_id,
    is_safe_identity_value,
    is_safe_public_text,
)

RESEARCH_CATALOG_ENTRY_ROLE = "research_catalog_entry"

_SUPPORTED_WORKFLOWS = frozenset(
    {
        WorkflowKind.MARKET,
        WorkflowKind.SIGNAL,
        WorkflowKind.STRATEGY,
        WorkflowKind.ROBUSTNESS,
        WorkflowKind.PREDICTIVE,
    }
)


def catalog_artifact_id(summary: RunSummary) -> str:
    """Return the stable projection id for one safely identifiable run."""
    candidate = f"catalog-{summary.workflow.value}-{summary.run_id}"
    if not is_safe_artifact_id(candidate):
        msg = f"run_id cannot form a safe public artifact identity: {summary.run_id!r}"
        raise UnsafePublicIdentityError(msg)
    return candidate


def build_catalog_artifact_input(
    summary: RunSummary,
    *,
    verdict: str | None = None,
) -> RawArtifactInput:
    """Build one unsanitized input for the catalog-entry allowlist.

    Only dashboard-supported research workflows are accepted. Optional
    identity values must remain conservative non-path strings; a run that
    fails this check is not safely identifiable and is not publishable.
    """
    if summary.workflow not in _SUPPORTED_WORKFLOWS:
        msg = f"workflow is not publishable in the research catalog: {summary.workflow.value!r}"
        raise UnsafePublicIdentityError(msg)

    _require_safe_identity("run_id", summary.run_id)
    _require_safe_identity("source_dataset_ref", summary.source_dataset_ref)
    _require_safe_identity("evaluation_timeframe", summary.evaluation_timeframe)
    _require_safe_identity("framework_version", summary.framework_version)
    _require_safe_identity("artifact_schema_version", summary.artifact_schema_version)
    _require_safe_identity("research_scope", summary.research_scope)
    _require_safe_identity("experiment_id", summary.experiment_id)
    _require_safe_text("title", summary.title)
    _require_safe_text("verdict", verdict)

    raw_payload: dict[str, Any] = {
        "workflow": summary.workflow.value,
        "run_id": summary.run_id,
        "title": summary.title,
        "created_at_utc": _isoformat(summary.created_at_utc),
        "source_dataset_ref": summary.source_dataset_ref,
        "evaluation_timeframe": summary.evaluation_timeframe,
        "framework_version": summary.framework_version,
        "artifact_schema_version": summary.artifact_schema_version,
        "research_scope": summary.research_scope,
        "experiment_id": summary.experiment_id,
        "time_range_start_utc": _isoformat(summary.time_range_start_utc),
        "time_range_end_utc": _isoformat(summary.time_range_end_utc),
        "verdict": verdict,
        # Deliberately supplied to prove that the sanitizer never copies it.
        "storage_path": summary.storage_path,
    }
    return RawArtifactInput(
        artifact_id=catalog_artifact_id(summary),
        artifact_role=RESEARCH_CATALOG_ENTRY_ROLE,
        raw_payload=raw_payload,
    )


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.utcoffset() is None:
        msg = f"public catalog timestamp must be timezone-aware: {value!r}"
        raise UnsafePublicIdentityError(msg)
    return value.isoformat()


def _require_safe_identity(field: str, value: str | None) -> None:
    if value is None:
        return
    if not is_safe_identity_value(value):
        msg = f"unsafe public {field}: {value!r}"
        raise UnsafePublicIdentityError(msg)


def _require_safe_text(field: str, value: str | None) -> None:
    if value is None:
        return
    if not is_safe_public_text(value):
        msg = f"unsafe or path-like public {field}: {value!r}"
        raise UnsafePublicIdentityError(msg)
