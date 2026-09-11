"""Pure presentation models for rich, projection-backed workflow evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from dashboard_app.publication.evidence import (
    LEGACY_ROBUSTNESS_EXPERIMENT_ID,
    ROBUSTNESS_RESEARCH_EVIDENCE_ROLE,
    SIGNAL_RESEARCH_EVIDENCE_ROLE,
)
from dashboard_app.publication.projection import PublicProjectionBundle


@dataclass(frozen=True, slots=True)
class ProjectedResearchEvidence:
    """One already-sanitized evidence artifact and its public tables."""

    artifact_id: str
    fields: Mapping[str, Any]

    def table(self, name: str) -> pa.Table | None:
        tables = self.fields.get("tables")
        if not isinstance(tables, Mapping):
            return None
        rows = tables.get(name)
        if not isinstance(rows, list):
            return None
        public_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
        return pa.Table.from_pylist(public_rows) if public_rows else None


@dataclass(frozen=True, slots=True)
class ParameterSweepSlice:
    """One projected parameter-sweep metric/axis selection."""

    metric: str
    x_axis: str
    y_axis: str | None

    @property
    def label(self) -> str:
        return f"{self.metric}: {self.x_axis}" + (f" x {self.y_axis}" if self.y_axis else "")


def signal_research_evidence(
    bundle: PublicProjectionBundle,
) -> tuple[ProjectedResearchEvidence, ...]:
    """Return projected Signal runs newest-first without filesystem discovery."""
    evidence = [
        ProjectedResearchEvidence(artifact_id=artifact.artifact_id, fields=artifact.fields)
        for artifact in bundle.artifacts.values()
        if artifact.artifact_role == SIGNAL_RESEARCH_EVIDENCE_ROLE
    ]
    return tuple(
        sorted(evidence, key=lambda item: str(item.fields.get("created_at_utc", "")), reverse=True)
    )


def legacy_robustness_evidence(
    bundle: PublicProjectionBundle,
) -> ProjectedResearchEvidence | None:
    """Resolve the one explicitly published demo, never a catalog/Strategy run."""
    artifact_id = f"robustness-research-evidence-{LEGACY_ROBUSTNESS_EXPERIMENT_ID}"
    artifact = bundle.artifacts.get(artifact_id)
    if artifact is None or artifact.artifact_role != ROBUSTNESS_RESEARCH_EVIDENCE_ROLE:
        return None
    return ProjectedResearchEvidence(artifact_id=artifact.artifact_id, fields=artifact.fields)


def parameter_sweep_slices(table: pa.Table) -> tuple[ParameterSweepSlice, ...]:
    """Return distinct projected sweep slices without deriving research facts."""
    required = {"metric", "x_axis", "x_value", "value"}
    if table.num_rows == 0 or not required.issubset(table.column_names):
        return ()
    rows = table.to_pylist()
    slices = {
        ParameterSweepSlice(
            metric=str(row["metric"]),
            x_axis=str(row["x_axis"]),
            y_axis=str(row["y_axis"]) if row.get("y_axis") else None,
        )
        for row in rows
        if row.get("metric") is not None and row.get("x_axis") is not None
    }
    return tuple(sorted(slices, key=lambda item: (item.metric, item.x_axis, item.y_axis or "")))


def filter_parameter_sweep(table: pa.Table, selected: ParameterSweepSlice) -> pa.Table:
    """Filter projected rows to the chosen presentation slice."""
    rows = [
        row
        for row in table.to_pylist()
        if row.get("metric") == selected.metric
        and row.get("x_axis") == selected.x_axis
        and (str(row["y_axis"]) if row.get("y_axis") else None) == selected.y_axis
    ]
    return pa.Table.from_pylist(rows) if rows else table.slice(0, 0)
