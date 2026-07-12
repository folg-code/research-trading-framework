"""Scope-aware Signal Research inspection helpers (S009-T009 spike support)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import assert_never, cast

import polars as pl

from tests.spike._signal_research_inspection import (
    InspectionSelection,
    build_inspection_selection,
    select_occurrence_row,
    select_outcome_row,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.signal_research import SignalResearchRunEnvelope
from trading_framework.research.scope import ResearchScope


@dataclass(frozen=True, slots=True)
class CombinedInspectionSelection:
    """One research fact row with optional context for chart inspection."""

    scope: ResearchScope
    fact_kind: str
    fact_id: str
    model_id: str
    selection: InspectionSelection
    context_met_at_available_at: bool | None = None
    market_model_id: str | None = None


def _observation_row(
    observations: pl.DataFrame,
    *,
    observation_index: int | None = None,
    observation_id: str | None = None,
) -> dict[str, object]:
    if len(observations) == 0:
        msg = "observations table is empty"
        raise ValidationError(msg)
    if observation_id is not None:
        filtered = observations.filter(pl.col("observation_id") == observation_id)
        if len(filtered) != 1:
            msg = f"observation_id not found or ambiguous: {observation_id}"
            raise ValidationError(msg)
        return filtered.row(0, named=True)
    index = observation_index if observation_index is not None else 0
    if index < 0 or index >= len(observations):
        msg = f"observation_index out of range: {index}"
        raise ValidationError(msg)
    return observations.row(index, named=True)


def _selection_from_outcome_join(
    *,
    fact_id: str,
    model_id: str,
    detected_at: datetime,
    available_at: datetime,
    direction: str,
    reference_price: float,
    outcomes: pl.DataFrame,
    horizon_bars: int,
) -> InspectionSelection:
    outcome = select_outcome_row(
        outcomes,
        occurrence_id=fact_id,
        horizon_bars=horizon_bars,
    )
    return InspectionSelection(
        occurrence_id=fact_id,
        signal_model_id=model_id,
        detected_at=detected_at,
        available_at=available_at,
        direction=direction,
        reference_price=reference_price,
        horizon_bars=horizon_bars,
        outcome_status=str(outcome["outcome_status"]) if outcome is not None else None,
        forward_return=(
            float(cast(float, outcome["forward_return"]))
            if outcome is not None and outcome["forward_return"] is not None
            else None
        ),
        mfe=(
            float(cast(float, outcome["mfe"]))
            if outcome is not None and outcome["mfe"] is not None
            else None
        ),
        mae=(
            float(cast(float, outcome["mae"]))
            if outcome is not None and outcome["mae"] is not None
            else None
        ),
        terminal_price=(
            float(cast(float, outcome["terminal_price"]))
            if outcome is not None and outcome["terminal_price"] is not None
            else None
        ),
    )


def build_combined_inspection_selection(
    envelope: SignalResearchRunEnvelope,
    *,
    scope: ResearchScope | None = None,
    fact_index: int | None = None,
    fact_id: str | None = None,
    horizon_bars: int,
) -> CombinedInspectionSelection:
    """Build scope-aware inspection selection from one persisted run envelope."""
    effective_scope = scope or envelope.manifest.effective_scope()
    if effective_scope is ResearchScope.SIGNAL_MODEL_ONLY:
        selection = build_inspection_selection(
            envelope.occurrences,
            envelope.outcomes,
            occurrence_index=fact_index,
            occurrence_id=fact_id,
            horizon_bars=horizon_bars,
        )
        return CombinedInspectionSelection(
            scope=effective_scope,
            fact_kind="occurrence",
            fact_id=selection.occurrence_id,
            model_id=selection.signal_model_id,
            selection=selection,
        )

    if effective_scope is ResearchScope.MARKET_MODEL_ONLY:
        observation = _observation_row(
            envelope.observations,
            observation_index=fact_index,
            observation_id=fact_id,
        )
        observation_id = str(observation["observation_id"])
        market_model_id = str(observation["market_model_id"])
        selection = _selection_from_outcome_join(
            fact_id=observation_id,
            model_id=market_model_id,
            detected_at=cast(datetime, observation["detected_at"]),
            available_at=cast(datetime, observation["available_at"]),
            direction="long",
            reference_price=float(cast(float, observation["reference_price"])),
            outcomes=envelope.outcomes,
            horizon_bars=horizon_bars,
        )
        return CombinedInspectionSelection(
            scope=effective_scope,
            fact_kind="observation",
            fact_id=observation_id,
            model_id=market_model_id,
            selection=selection,
            market_model_id=market_model_id,
        )

    if effective_scope is ResearchScope.MARKET_AND_SIGNAL:
        occurrence = select_occurrence_row(
            envelope.occurrences,
            occurrence_index=fact_index,
            occurrence_id=fact_id,
        )
        occurrence_id = str(occurrence["occurrence_id"])
        context_rows = envelope.context.filter(pl.col("occurrence_id") == occurrence_id)
        if len(context_rows) != 1:
            msg = f"context row missing or ambiguous for occurrence: {occurrence_id}"
            raise ValidationError(msg)
        context_row = context_rows.row(0, named=True)
        selection = _selection_from_outcome_join(
            fact_id=occurrence_id,
            model_id=str(occurrence["signal_model_id"]),
            detected_at=cast(datetime, occurrence["detected_at"]),
            available_at=cast(datetime, occurrence["available_at"]),
            direction=str(occurrence["direction"]),
            reference_price=float(cast(float, occurrence["reference_price"])),
            outcomes=envelope.outcomes,
            horizon_bars=horizon_bars,
        )
        return CombinedInspectionSelection(
            scope=effective_scope,
            fact_kind="occurrence",
            fact_id=occurrence_id,
            model_id=selection.signal_model_id,
            selection=selection,
            context_met_at_available_at=bool(context_row["context_met_at_available_at"]),
            market_model_id=str(context_row["market_model_id"]),
        )

    assert_never(effective_scope)
