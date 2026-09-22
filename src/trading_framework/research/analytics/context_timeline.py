"""Dated market-context series and run-length persistence.

Phase 18, 18B Milestone 1 (Sprint 073) / D-P18B-04. Reuses 18A's
``state_context_aliases`` mechanism (D-P18-02) as-is: resolve the run's
Market Model, recompute Market Analysis components over the published
dataset, filter to ``ComponentKind.STATE`` columns the model's expression
actually references. Unlike ``context_expectancy`` (Strategy Research,
joins to trades), this module has no trade population to join against --
it publishes the raw dated series itself (``context_timeline``) and its
run-length encoding (``context_persistence``).
"""

from __future__ import annotations

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research.analytics.market_model_context import state_context_aliases

CONTEXT_TIMELINE_SCHEMA_VERSION = "signal_research_context_timeline.v1"
CONTEXT_PERSISTENCE_SCHEMA_VERSION = "signal_research_context_persistence.v1"


def context_timeline_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "component_id": pl.String(),
        "observed_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "label": pl.String(),
    }


def context_persistence_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "component_id": pl.String(),
        "label": pl.String(),
        "start_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "end_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "duration_bars": pl.Int64(),
    }


def empty_context_timeline_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=context_timeline_schema())


def empty_context_persistence_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=context_persistence_schema())


def compute_context_timeline(
    *,
    run_id: str,
    market_model: MarketModelDefinition,
    frame: AnalysisFrame,
    registry: ComponentRegistry | None = None,
) -> pl.DataFrame:
    """Raw dated series for every qualifying STATE-kind context component.

    A run whose Market Model references no ``STATE``-kind component
    produces an empty table, not an error. Bounding for publication (a
    per-bar dense series can be very large) is the publisher's job, not
    this function's -- it always returns the full series.
    """
    aliases = state_context_aliases(market_model=market_model, frame=frame, registry=registry)
    if not aliases:
        return empty_context_timeline_dataframe()

    rows: list[dict[str, object]] = []
    for alias, component_id in aliases.items():
        values = frame.columns[alias]
        for observed_at, value in zip(frame.timestamps, values, strict=True):
            rows.append(
                {
                    "schema_version": CONTEXT_TIMELINE_SCHEMA_VERSION,
                    "run_id": run_id,
                    "component_id": component_id,
                    "observed_at": observed_at,
                    "label": str(value),
                }
            )
    if not rows:
        return empty_context_timeline_dataframe()
    return pl.DataFrame(rows, schema=context_timeline_schema())


def compute_context_persistence(
    *,
    run_id: str,
    market_model: MarketModelDefinition,
    frame: AnalysisFrame,
    registry: ComponentRegistry | None = None,
) -> pl.DataFrame:
    """Run-length encoding of each qualifying context component's series.

    One row per maximal run of consecutive bars holding the same label.
    ``end_at`` is null for a run still open at the series' last
    observation -- an explicit "not yet resolved" run, not a fabricated
    end. No minimum-duration threshold.
    """
    aliases = state_context_aliases(market_model=market_model, frame=frame, registry=registry)
    if not aliases:
        return empty_context_persistence_dataframe()

    timestamps = frame.timestamps
    rows: list[dict[str, object]] = []
    for alias, component_id in aliases.items():
        values = frame.columns[alias]
        if not values:
            continue
        run_start_idx = 0
        current_label = str(values[0])
        for idx in range(1, len(values)):
            label = str(values[idx])
            if label != current_label:
                rows.append(
                    {
                        "schema_version": CONTEXT_PERSISTENCE_SCHEMA_VERSION,
                        "run_id": run_id,
                        "component_id": component_id,
                        "label": current_label,
                        "start_at": timestamps[run_start_idx],
                        "end_at": timestamps[idx],
                        "duration_bars": idx - run_start_idx,
                    }
                )
                run_start_idx = idx
                current_label = label
        rows.append(
            {
                "schema_version": CONTEXT_PERSISTENCE_SCHEMA_VERSION,
                "run_id": run_id,
                "component_id": component_id,
                "label": current_label,
                "start_at": timestamps[run_start_idx],
                "end_at": None,
                "duration_bars": len(values) - run_start_idx,
            }
        )
    if not rows:
        return empty_context_persistence_dataframe()
    return pl.DataFrame(rows, schema=context_persistence_schema())
