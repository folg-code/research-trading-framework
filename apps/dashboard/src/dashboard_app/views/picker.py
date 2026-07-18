"""Shared Streamlit helpers for selecting catalog runs."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from dashboard_app.contracts import RunSummary


def format_run_label(summary: RunSummary, *, disambiguator: str | None = None) -> str:
    """Build a human-readable picker label (date + title + dataset/TF).

    ``run_id`` is omitted from the primary label; pass ``disambiguator`` when two
    runs would otherwise collide.
    """
    date = (
        summary.created_at_utc.strftime("%Y-%m-%d %H:%M")
        if summary.created_at_utc is not None
        else "undated"
    )
    parts: list[str] = [date, summary.title]
    dataset = summary.source_dataset_ref
    if dataset:
        if summary.evaluation_timeframe:
            parts.append(f"{dataset} · {summary.evaluation_timeframe}")
        else:
            parts.append(dataset)
    elif summary.evaluation_timeframe:
        parts.append(summary.evaluation_timeframe)
    if disambiguator:
        parts.append(f"#{disambiguator}")
    return " · ".join(parts)


def run_picker_options(runs: Sequence[RunSummary]) -> dict[str, RunSummary]:
    """Map unique human labels to run summaries (newest-first input preferred)."""
    counts: dict[str, int] = {}
    for summary in runs:
        base = format_run_label(summary)
        counts[base] = counts.get(base, 0) + 1

    seen: dict[str, int] = {}
    options: dict[str, RunSummary] = {}
    for summary in runs:
        base = format_run_label(summary)
        if counts[base] == 1:
            label = base
        else:
            seen[base] = seen.get(base, 0) + 1
            label = format_run_label(summary, disambiguator=summary.run_id)
        options[label] = summary
    return options


def select_catalog_run(
    runs: Sequence[RunSummary],
    *,
    label: str = "Run",
    key: str,
) -> RunSummary:
    """Render a selectbox over human-readable catalog labels."""
    options = run_picker_options(runs)
    selected = st.selectbox(label, options=list(options), key=key)
    return options[selected]


def render_run_identity(summary: RunSummary, *, heading: str = "Identity") -> None:
    """Show human metadata prominently; tuck opaque ids into an expander."""
    cols = st.columns(4)
    cols[0].write(
        f"**created:** `{summary.created_at_utc.isoformat() if summary.created_at_utc else '—'}`"
    )
    cols[1].write(f"**dataset:** `{summary.source_dataset_ref or '—'}`")
    cols[2].write(f"**timeframe:** `{summary.evaluation_timeframe or '—'}`")
    cols[3].write(f"**workflow:** `{summary.workflow.value}`")
    with st.expander(heading, expanded=False):
        st.write(
            {
                "title": summary.title,
                "run_id": summary.run_id,
                "experiment_id": summary.experiment_id,
                "research_scope": summary.research_scope,
                "storage_path": summary.storage_path,
            }
        )
