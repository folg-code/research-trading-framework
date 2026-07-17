"""Helpers for Market / Signal Research dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from dashboard_app.catalog import list_runs
from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.query import DashboardQueryService

_SIGNAL_TABLES = (
    "summary_metrics",
    "grouped_summaries",
    "distribution_summaries",
    "conditional_comparison",
    "join_diagnostics",
    "metric_histograms",
    "quality_warnings",
)


@dataclass(frozen=True, slots=True)
class ResearchRunArtifacts:
    """Loaded analytics tables for one market/signal research run."""

    summary: RunSummary
    tables: dict[str, pa.Table]


def list_research_runs(storage_root: Path) -> tuple[RunSummary, ...]:
    """Return MARKET and SIGNAL catalog rows newest-first."""
    catalog = list_runs(storage_root)
    return tuple(
        item for item in catalog.runs if item.workflow in {WorkflowKind.MARKET, WorkflowKind.SIGNAL}
    )


def load_research_run(
    service: DashboardQueryService,
    summary: RunSummary,
) -> ResearchRunArtifacts:
    """Load available analytics Parquet tables for one research run."""
    run_dir = Path(summary.storage_path)
    tables: dict[str, pa.Table] = {}
    for name in _SIGNAL_TABLES:
        table = service.read_parquet_columns(run_dir / "analytics" / f"{name}.parquet")
        if table.num_rows > 0 or (run_dir / "analytics" / f"{name}.parquet").is_file():
            tables[name] = table
    return ResearchRunArtifacts(summary=summary, tables=tables)
