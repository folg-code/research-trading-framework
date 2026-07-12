"""SignalOccurrence — provider-independent signal event facts (Strategy domain)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.strategy.reference_price import ReferencePricePolicy, resolve_reference_price
from trading_framework.time.models.timeframe import Timeframe


def _occurrence_schema() -> dict[str, pl.DataType]:
    return {
        "occurrence_id": pl.String(),
        "signal_model_id": pl.String(),
        "detected_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "direction": pl.String(),
        "reference_price": pl.Float64(),
        "instrument": pl.String(),
        "evaluation_timeframe": pl.String(),
        "source_dataset_ref": pl.String(),
    }


@dataclass(frozen=True, slots=True)
class OccurrenceMaterializationContext:
    """Run-scoped metadata required to materialize occurrence facts."""

    signal_model_id: str
    instrument: str
    evaluation_timeframe: Timeframe
    source_dataset_ref: str
    reference_price_policy: ReferencePricePolicy = ReferencePricePolicy.CLOSE_AT_DETECTED_AT


def derive_occurrence_id(
    *,
    signal_model_id: str,
    detected_at: datetime,
    direction: str,
) -> str:
    """Stable occurrence identity within one research run."""
    payload = f"{signal_model_id}|{detected_at.isoformat()}|{direction}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def empty_signal_occurrences_dataframe() -> pl.DataFrame:
    """Return an empty occurrences table with the canonical schema."""
    return pl.DataFrame(schema=_occurrence_schema())


def materialize_signal_occurrences(
    emissions: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    context: OccurrenceMaterializationContext,
    market_view: AnalysisDataView | None = None,
) -> pl.DataFrame:
    """Build occurrence facts from sparse Signal Model emissions.

    Expects emission columns: ``detected_at``, ``available_at``, ``direction``.
    Research-only fields must not be added here.
    """
    if len(emissions) == 0:
        return empty_signal_occurrences_dataframe()

    rows: list[dict[str, Any]] = []
    for row in emissions.iter_rows(named=True):
        detected_at = row["detected_at"]
        direction = row["direction"]
        reference_price = resolve_reference_price(
            context.reference_price_policy,
            detected_at=detected_at,
            frame=frame,
            market_view=market_view,
        )
        rows.append(
            {
                "occurrence_id": derive_occurrence_id(
                    signal_model_id=context.signal_model_id,
                    detected_at=detected_at,
                    direction=direction,
                ),
                "signal_model_id": context.signal_model_id,
                "detected_at": detected_at,
                "available_at": row["available_at"],
                "direction": direction,
                "reference_price": reference_price,
                "instrument": context.instrument,
                "evaluation_timeframe": context.evaluation_timeframe.value,
                "source_dataset_ref": context.source_dataset_ref,
            }
        )
    return pl.DataFrame(rows, schema=_occurrence_schema())
