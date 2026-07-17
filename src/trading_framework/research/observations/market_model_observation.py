"""MarketModelObservation — research sampling points from dense market model state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.strategy.reference_price import (
    ReferencePricePolicy,
    build_reference_price_lookup,
    resolve_reference_price,
)
from trading_framework.time.models.timeframe import Timeframe


class MarketModelObservationPolicy(StrEnum):
    """How research selects observation points from dense market model state."""

    TRUE_EDGE = "true_edge"


def _observation_schema() -> dict[str, pl.DataType]:
    return {
        "observation_id": pl.String(),
        "market_model_id": pl.String(),
        "detected_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "reference_price": pl.Float64(),
        "instrument": pl.String(),
        "evaluation_timeframe": pl.String(),
        "source_dataset_ref": pl.String(),
    }


@dataclass(frozen=True, slots=True)
class ObservationMaterializationContext:
    """Run-scoped metadata required to materialize market model observations."""

    market_model_id: str
    instrument: str
    evaluation_timeframe: Timeframe
    source_dataset_ref: str
    reference_price_policy: ReferencePricePolicy = ReferencePricePolicy.CLOSE_AT_DETECTED_AT
    policy: MarketModelObservationPolicy = MarketModelObservationPolicy.TRUE_EDGE


def derive_observation_id(*, market_model_id: str, detected_at: datetime) -> str:
    """Stable observation identity within one research run."""
    payload = f"{market_model_id}|{detected_at.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def empty_market_model_observations_dataframe() -> pl.DataFrame:
    """Return an empty observations table with the canonical schema."""
    return pl.DataFrame(schema=_observation_schema())


def validate_observations_dataframe(frame: pl.DataFrame) -> None:
    """Validate market model observation fact table columns."""
    expected = empty_market_model_observations_dataframe()
    if frame.columns != expected.columns:
        msg = f"observations columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


def materialize_market_model_observations(
    market_state: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    context: ObservationMaterializationContext,
    market_view: AnalysisDataView | None = None,
) -> pl.DataFrame:
    """Build observation facts from dense market model state.

    Expects market state columns: ``timestamp``, ``available_at``, ``model_result``,
    ``market_model_id``.
    """
    if len(market_state) == 0:
        return empty_market_model_observations_dataframe()

    sorted_state = market_state.sort("timestamp")
    previous_result = sorted_state["model_result"].shift(1).fill_null(False)
    edges = sorted_state.filter(pl.col("model_result") & ~previous_result)
    if len(edges) == 0:
        return empty_market_model_observations_dataframe()

    lookup = build_reference_price_lookup(frame, market_view)
    rows: list[dict[str, Any]] = []
    for row in edges.iter_rows(named=True):
        detected_at = row["timestamp"]
        reference_price = resolve_reference_price(
            context.reference_price_policy,
            detected_at=detected_at,
            frame=frame,
            market_view=market_view,
            lookup=lookup,
        )
        rows.append(
            {
                "observation_id": derive_observation_id(
                    market_model_id=context.market_model_id,
                    detected_at=detected_at,
                ),
                "market_model_id": context.market_model_id,
                "detected_at": detected_at,
                "available_at": row["available_at"],
                "reference_price": reference_price,
                "instrument": context.instrument,
                "evaluation_timeframe": context.evaluation_timeframe.value,
                "source_dataset_ref": context.source_dataset_ref,
            }
        )
    return pl.DataFrame(rows, schema=_observation_schema())
