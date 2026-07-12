"""Forward outcome calculator — long-format outcome facts from occurrences."""

from __future__ import annotations

import math
from typing import Any

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression.references import MarketField
from trading_framework.research.outcomes.definition import (
    ForwardOutcomeDefinition,
    IncompleteHorizonPolicy,
    OutcomeStatus,
)
from trading_framework.research.outcomes.ohlcv import timestamp_index
from trading_framework.signal_model.definitions import SignalDirection


def _outcome_schema() -> dict[str, pl.DataType]:
    return {
        "occurrence_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "outcome_status": pl.String(),
        "terminal_price": pl.Float64(),
        "forward_return": pl.Float64(),
        "mfe": pl.Float64(),
        "mae": pl.Float64(),
    }


def empty_forward_outcomes_dataframe() -> pl.DataFrame:
    """Return an empty outcomes table with the canonical long-format schema."""
    return pl.DataFrame(schema=_outcome_schema())


def _ohlcv_series(
    ohlcv: dict[str, tuple[float, ...]],
    field: MarketField,
) -> tuple[float, ...]:
    key = field.value
    if key not in ohlcv:
        msg = f"ohlcv columns missing required field: {key}"
        raise KeyError(msg)
    return ohlcv[key]


def _direction_normalize_return(*, raw_return: float, direction: str) -> float:
    if direction == SignalDirection.SHORT.value:
        return -raw_return
    return raw_return


def _compute_excursions(
    *,
    reference_price: float,
    direction: str,
    highs: list[float],
    lows: list[float],
) -> tuple[float, float]:
    if not math.isfinite(reference_price) or reference_price == 0.0:
        return math.nan, math.nan

    high_returns = [high / reference_price - 1.0 for high in highs]
    low_returns = [low / reference_price - 1.0 for low in lows]

    if direction == SignalDirection.SHORT.value:
        favorable = [-low_return for low_return in low_returns]
        adverse = [-high_return for high_return in high_returns]
    else:
        favorable = high_returns
        adverse = low_returns

    mfe = max(max(favorable), 0.0)
    mae = min(min(adverse), 0.0)
    return mfe, mae


def _null_outcome_row(
    *,
    occurrence_id: str,
    horizon: int,
    status: OutcomeStatus,
) -> dict[str, Any]:
    return {
        "occurrence_id": occurrence_id,
        "horizon_bars": horizon,
        "outcome_status": status.value,
        "terminal_price": None,
        "forward_return": None,
        "mfe": None,
        "mae": None,
    }


def compute_forward_outcomes(
    occurrences: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    definition: ForwardOutcomeDefinition,
) -> pl.DataFrame:
    """Compute long-format forward outcome rows for one horizon definition."""
    if len(occurrences) == 0:
        return empty_forward_outcomes_dataframe()

    index_by_timestamp = timestamp_index(frame)
    close = _ohlcv_series(ohlcv, MarketField.CLOSE)
    terminal = _ohlcv_series(ohlcv, definition.terminal_price_field)
    high = _ohlcv_series(ohlcv, definition.excursion_high_field)
    low = _ohlcv_series(ohlcv, definition.excursion_low_field)
    horizon = definition.horizon_bars
    rows: list[dict[str, Any]] = []

    for occurrence in occurrences.iter_rows(named=True):
        detected_at = occurrence["detected_at"]
        signal_index = index_by_timestamp.get(detected_at)
        reference_price = occurrence["reference_price"]
        direction = occurrence["direction"]
        occurrence_id = occurrence["occurrence_id"]

        if signal_index is None or not math.isfinite(reference_price):
            rows.append(
                _null_outcome_row(
                    occurrence_id=occurrence_id,
                    horizon=horizon,
                    status=OutcomeStatus.INSUFFICIENT_DATA,
                )
            )
            continue

        window_start = signal_index + 1
        window_end = signal_index + horizon
        if window_end >= len(frame.timestamps):
            if definition.incomplete_horizon_policy == IncompleteHorizonPolicy.EMIT_WITH_STATUS:
                rows.append(
                    _null_outcome_row(
                        occurrence_id=occurrence_id,
                        horizon=horizon,
                        status=OutcomeStatus.INCOMPLETE_HORIZON,
                    )
                )
            continue

        window_highs = [high[index] for index in range(window_start, window_end + 1)]
        window_lows = [low[index] for index in range(window_start, window_end + 1)]
        window_terminals = [terminal[index] for index in range(window_start, window_end + 1)]
        window_closes = [close[index] for index in range(window_start, window_end + 1)]

        if any(
            not math.isfinite(value)
            for value in (*window_highs, *window_lows, *window_terminals, *window_closes)
        ):
            rows.append(
                _null_outcome_row(
                    occurrence_id=occurrence_id,
                    horizon=horizon,
                    status=OutcomeStatus.INSUFFICIENT_DATA,
                )
            )
            continue

        terminal_price = terminal[window_end]
        raw_return = terminal_price / reference_price - 1.0
        forward_return = _direction_normalize_return(raw_return=raw_return, direction=direction)
        mfe, mae = _compute_excursions(
            reference_price=reference_price,
            direction=direction,
            highs=window_highs,
            lows=window_lows,
        )
        rows.append(
            {
                "occurrence_id": occurrence_id,
                "horizon_bars": horizon,
                "outcome_status": OutcomeStatus.COMPLETE.value,
                "terminal_price": terminal_price,
                "forward_return": forward_return,
                "mfe": mfe,
                "mae": mae,
            }
        )

    return pl.DataFrame(rows, schema=_outcome_schema())


def compute_forward_outcomes_for_horizons(
    occurrences: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    horizons: tuple[int, ...],
    definition: ForwardOutcomeDefinition | None = None,
) -> pl.DataFrame:
    """Compute long-format outcomes for multiple horizons (one row per occurrence x horizon)."""
    if not horizons:
        return empty_forward_outcomes_dataframe()

    base = definition or ForwardOutcomeDefinition(horizon_bars=horizons[0])
    frames = [
        compute_forward_outcomes(
            occurrences,
            frame=frame,
            ohlcv=ohlcv,
            definition=ForwardOutcomeDefinition(
                horizon_bars=horizon,
                reference_price_policy=base.reference_price_policy,
                terminal_price_field=base.terminal_price_field,
                excursion_high_field=base.excursion_high_field,
                excursion_low_field=base.excursion_low_field,
                incomplete_horizon_policy=base.incomplete_horizon_policy,
            ),
        )
        for horizon in horizons
    ]
    return pl.concat(frames) if frames else empty_forward_outcomes_dataframe()
