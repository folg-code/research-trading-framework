"""Presentation helpers for the path-free public research catalog."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from dashboard_app.contracts import WorkflowKind
from dashboard_app.formatting import (
    format_created_at,
    humanize_dataset_ref,
    humanize_model_id,
    instrument_from_dataset_ref,
)
from dashboard_app.publication.catalog_index import PublicCatalogRun


@dataclass(frozen=True, slots=True)
class PublicCatalogRow:
    """One human-readable public run row with no filesystem fields."""

    created: str
    workflow: str
    instrument: str
    timeframe: str
    time_range: str
    dataset: str
    model: str
    title: str
    run_id: str
    experiment_id: str
    research_scope: str
    verdict: str


def build_public_catalog_row(run: PublicCatalogRun) -> PublicCatalogRow:
    """Map a projected run into display-only columns."""
    return PublicCatalogRow(
        created=format_created_at(run.created_at_utc),
        workflow=run.workflow.value,
        instrument=instrument_from_dataset_ref(run.source_dataset_ref) or "—",
        timeframe=run.evaluation_timeframe or "—",
        time_range=_format_time_range(run),
        dataset=humanize_dataset_ref(run.source_dataset_ref),
        model=_model_from_title(run.title),
        title=run.title,
        run_id=run.run_id,
        experiment_id=run.experiment_id or run.run_id,
        research_scope=run.research_scope or "—",
        verdict=run.verdict or "NO VERDICT",
    )


def filter_public_catalog_runs(
    runs: Sequence[PublicCatalogRun],
    *,
    workflow: WorkflowKind | None = None,
    instrument: str | None = None,
    timeframe: str | None = None,
    model_query: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[PublicCatalogRun, ...]:
    """Apply public-catalog filters with AND semantics."""
    selected: list[PublicCatalogRun] = []
    query = (model_query or "").strip().lower()
    for run in runs:
        if workflow is not None and run.workflow is not workflow:
            continue
        if instrument and instrument != "All":
            found = instrument_from_dataset_ref(run.source_dataset_ref)
            if found != instrument:
                continue
        if timeframe and timeframe != "All" and (run.evaluation_timeframe or "") != timeframe:
            continue
        if query and query not in run.title.lower():
            continue
        if date_from is not None or date_to is not None:
            if run.created_at_utc is None:
                continue
            created = run.created_at_utc.date()
            if date_from is not None and created < date_from:
                continue
            if date_to is not None and created > date_to:
                continue
        selected.append(run)
    return tuple(selected)


def public_catalog_filter_options(
    runs: Sequence[PublicCatalogRun],
) -> dict[str, tuple[str, ...]]:
    """Return unique, sorted instrument and timeframe filter values."""
    instruments = {
        instrument
        for run in runs
        if (instrument := instrument_from_dataset_ref(run.source_dataset_ref)) is not None
    }
    timeframes = {run.evaluation_timeframe for run in runs if run.evaluation_timeframe}
    return {
        "instruments": tuple(sorted(instruments)),
        "timeframes": tuple(sorted(timeframes)),
    }


def _model_from_title(title: str) -> str:
    parts = [part.strip() for part in title.split(" · ") if part.strip()]
    return humanize_model_id(parts[1] if len(parts) >= 2 else title)


def _format_time_range(run: PublicCatalogRun) -> str:
    start = run.time_range_start_utc
    end = run.time_range_end_utc
    if start is None or end is None:
        return "—"
    return f"{start.date().isoformat()} → {end.date().isoformat()}"
