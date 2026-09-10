"""Pure view models for one representative public evidence view per workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog_index import PublicCatalogRun
from dashboard_app.publication.projection import PublicProjectionBundle


@dataclass(frozen=True, slots=True)
class DatasetEvidenceView:
    """One DatasetRef identity copied from the latest projected research run."""

    source_dataset_ref: str
    evaluation_timeframe: str | None
    time_range_start_utc: datetime | None
    time_range_end_utc: datetime | None
    referenced_by_run_id: str


def runs_for_workflow(
    runs: Sequence[PublicCatalogRun], workflow: WorkflowKind
) -> tuple[PublicCatalogRun, ...]:
    """Return projected runs for one independent workflow in bundle order."""
    return tuple(run for run in runs if run.workflow is workflow)


def representative_dataset_evidence(
    runs: Sequence[PublicCatalogRun],
) -> DatasetEvidenceView | None:
    """Return the latest run's persisted DatasetRef identity without inference."""
    run = next((item for item in runs if item.source_dataset_ref is not None), None)
    if run is None or run.source_dataset_ref is None:
        return None
    return DatasetEvidenceView(
        source_dataset_ref=run.source_dataset_ref,
        evaluation_timeframe=run.evaluation_timeframe,
        time_range_start_utc=run.time_range_start_utc,
        time_range_end_utc=run.time_range_end_utc,
        referenced_by_run_id=run.run_id,
    )


def projected_role_fields_for_run(
    bundle: PublicProjectionBundle,
    *,
    artifact_role: str,
    run_id: str,
) -> Mapping[str, Any] | None:
    """Find one explicitly run-bound projected artifact by role and identity.

    The publication artifact naming conventions are deterministic. No path is
    built and no private artifact is opened at render time.
    """
    prefix_by_role = {
        "strategy_research_run_summary": "strategy-research-run-",
        "predictive_run_metrics": "predictive-run-metrics-",
        "predictive_run_verdict": "predictive-run-verdict-",
        "predictive_threshold_sensitivity": "predictive-threshold-sensitivity-",
    }
    prefix = prefix_by_role.get(artifact_role)
    if prefix is None:
        return None
    artifact = bundle.artifacts.get(f"{prefix}{run_id}")
    if artifact is None or artifact.artifact_role != artifact_role:
        return None
    return artifact.fields


def format_evidence_time_range(
    start: datetime | None,
    end: datetime | None,
) -> str:
    """Format an explicitly persisted research range, preserving absence."""
    if start is None or end is None:
        return "—"
    return f"{start.date().isoformat()} → {end.date().isoformat()}"
