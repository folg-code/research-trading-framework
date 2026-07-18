"""Catalog filtering and row presentation for Research Catalog."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.formatting import (
    format_created_at,
    humanize_dataset_ref,
    humanize_model_id,
    instrument_from_dataset_ref,
)


@dataclass(frozen=True, slots=True)
class CatalogRow:
    """One human-readable catalog table row."""

    workflow: str
    created: str
    instrument: str
    timeframe: str
    dataset: str
    model: str
    title: str
    run_id: str
    storage_path: str
    source_dataset_ref: str
    research_scope: str


def build_catalog_row(summary: RunSummary) -> CatalogRow:
    """Map a RunSummary into public catalog columns."""
    instrument = instrument_from_dataset_ref(summary.source_dataset_ref) or "—"
    model = _model_from_title(summary.title)
    return CatalogRow(
        workflow=summary.workflow.value,
        created=format_created_at(summary.created_at_utc),
        instrument=instrument,
        timeframe=summary.evaluation_timeframe or "—",
        dataset=humanize_dataset_ref(summary.source_dataset_ref),
        model=model,
        title=summary.title,
        run_id=summary.run_id,
        storage_path=summary.storage_path,
        source_dataset_ref=summary.source_dataset_ref or "—",
        research_scope=summary.research_scope or "—",
    )


def filter_catalog_runs(
    runs: Sequence[RunSummary],
    *,
    workflow: WorkflowKind | None = None,
    instrument: str | None = None,
    timeframe: str | None = None,
    model_query: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[RunSummary, ...]:
    """Apply Research Catalog filters (AND semantics)."""
    selected: list[RunSummary] = []
    query = (model_query or "").strip().lower()
    for item in runs:
        if workflow is not None and item.workflow is not workflow:
            continue
        if instrument and instrument != "All":
            found = instrument_from_dataset_ref(item.source_dataset_ref)
            if found != instrument:
                continue
        if timeframe and timeframe != "All" and (item.evaluation_timeframe or "") != timeframe:
            continue
        if query and query not in item.title.lower():
            continue
        if date_from is not None or date_to is not None:
            created = item.created_at_utc
            if created is None:
                continue
            day = created.date() if isinstance(created, datetime) else None
            if day is None:
                continue
            if date_from is not None and day < date_from:
                continue
            if date_to is not None and day > date_to:
                continue
        selected.append(item)
    return tuple(selected)


def catalog_filter_options(runs: Sequence[RunSummary]) -> dict[str, tuple[str, ...]]:
    """Distinct instrument / timeframe values for filter widgets."""
    instruments = sorted(
        {
            instrument_from_dataset_ref(item.source_dataset_ref)
            for item in runs
            if instrument_from_dataset_ref(item.source_dataset_ref)
        }
    )
    timeframes = sorted({item.evaluation_timeframe for item in runs if item.evaluation_timeframe})
    return {
        "instruments": tuple(instruments),
        "timeframes": tuple(timeframes),
    }


def _model_from_title(title: str) -> str:
    if " · " not in title:
        return humanize_model_id(title)
    # "Strategy · high_vol_… · signal foo" → humanize middle token
    parts = [part.strip() for part in title.split(" · ") if part.strip()]
    if len(parts) >= 2:
        return humanize_model_id(parts[1])
    return humanize_model_id(title)
