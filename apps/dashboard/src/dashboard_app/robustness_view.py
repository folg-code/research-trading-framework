"""Helpers for Strategy Robustness dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from dashboard_app.catalog import list_runs
from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.query import DashboardQueryService

_ROBUSTNESS_TABLES = (
    "parameter_sweep_rankings",
    "parameter_sweep_heatmap",
    "walk_forward_folds",
    "walk_forward_equity",
    "stress_comparison",
    "monte_carlo_distributions",
    "monte_carlo_tails",
)


@dataclass(frozen=True, slots=True)
class RobustnessExperimentArtifacts:
    """Loaded analytics tables for one robustness experiment."""

    summary: RunSummary
    tables: dict[str, pa.Table]
    verdict: dict[str, object] | None


def list_robustness_experiments(storage_root: Path) -> tuple[RunSummary, ...]:
    """Return ROBUSTNESS catalog rows newest-first."""
    catalog = list_runs(storage_root)
    return tuple(item for item in catalog.runs if item.workflow is WorkflowKind.ROBUSTNESS)


def load_robustness_experiment(
    service: DashboardQueryService,
    summary: RunSummary,
) -> RobustnessExperimentArtifacts:
    """Load Parquet analytics (and optional verdict.json) for one experiment."""
    experiment_dir = Path(summary.storage_path)
    tables: dict[str, pa.Table] = {}
    for name in _ROBUSTNESS_TABLES:
        path = experiment_dir / "analytics" / f"{name}.parquet"
        table = service.read_parquet_columns(path)
        if path.is_file():
            tables[name] = table

    verdict: dict[str, object] | None = None
    verdict_path = experiment_dir / "analytics" / "verdict.json"
    if verdict_path.is_file():
        import json

        payload = json.loads(verdict_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            verdict = payload
    return RobustnessExperimentArtifacts(summary=summary, tables=tables, verdict=verdict)
