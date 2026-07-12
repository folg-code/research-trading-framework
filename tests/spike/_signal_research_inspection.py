"""Pure helpers for Signal Research occurrence inspection (spike support)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.signal_model.definitions import SignalDirection


@dataclass(frozen=True, slots=True)
class InspectionSelection:
    """One occurrence and optional outcome row for inspection."""

    occurrence_id: str
    signal_model_id: str
    detected_at: datetime
    available_at: datetime
    direction: str
    reference_price: float
    horizon_bars: int
    outcome_status: str | None
    forward_return: float | None
    mfe: float | None
    mae: float | None
    terminal_price: float | None


@dataclass(frozen=True, slots=True)
class InspectionWindow:
    """OHLCV slice around one occurrence with evaluation-grid indices."""

    timestamps: tuple[datetime, ...]
    opens: tuple[float, ...]
    highs: tuple[float, ...]
    lows: tuple[float, ...]
    closes: tuple[float, ...]
    signal_index: int
    horizon_end_index: int | None
    horizon_end_timestamp: datetime | None


def select_occurrence_row(
    occurrences: pl.DataFrame,
    *,
    occurrence_index: int | None = None,
    occurrence_id: str | None = None,
) -> dict[str, object]:
    """Select one occurrence row by index or id."""
    if len(occurrences) == 0:
        msg = "occurrences table is empty"
        raise ValidationError(msg)
    if occurrence_id is not None:
        filtered = occurrences.filter(pl.col("occurrence_id") == occurrence_id)
        if len(filtered) != 1:
            msg = f"occurrence_id not found or ambiguous: {occurrence_id}"
            raise ValidationError(msg)
        return filtered.row(0, named=True)
    index = occurrence_index if occurrence_index is not None else 0
    if index < 0 or index >= len(occurrences):
        msg = f"occurrence_index out of range: {index}"
        raise ValidationError(msg)
    return occurrences.row(index, named=True)


def select_outcome_row(
    outcomes: pl.DataFrame,
    *,
    occurrence_id: str,
    horizon_bars: int,
) -> dict[str, object] | None:
    """Select one outcome row for an occurrence and horizon."""
    filtered = outcomes.filter(
        (pl.col("occurrence_id") == occurrence_id) & (pl.col("horizon_bars") == horizon_bars)
    )
    if len(filtered) == 0:
        return None
    if len(filtered) != 1:
        msg = f"ambiguous outcome rows for {occurrence_id} horizon={horizon_bars}"
        raise ValidationError(msg)
    return filtered.row(0, named=True)


def build_inspection_selection(
    occurrences: pl.DataFrame,
    outcomes: pl.DataFrame,
    *,
    occurrence_index: int | None = None,
    occurrence_id: str | None = None,
    horizon_bars: int,
) -> InspectionSelection:
    """Build inspection selection from persisted run facts."""
    occurrence = select_occurrence_row(
        occurrences,
        occurrence_index=occurrence_index,
        occurrence_id=occurrence_id,
    )
    outcome = select_outcome_row(
        outcomes,
        occurrence_id=str(occurrence["occurrence_id"]),
        horizon_bars=horizon_bars,
    )
    return InspectionSelection(
        occurrence_id=str(occurrence["occurrence_id"]),
        signal_model_id=str(occurrence["signal_model_id"]),
        detected_at=cast(datetime, occurrence["detected_at"]),
        available_at=cast(datetime, occurrence["available_at"]),
        direction=str(occurrence["direction"]),
        reference_price=float(cast(float, occurrence["reference_price"])),
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


def bars_to_window(
    bars: list[MarketBar],
    *,
    detected_at: datetime,
    horizon_bars: int,
    padding_bars: int,
) -> InspectionWindow:
    """Slice ordered bars around one occurrence for chart rendering."""
    if not bars:
        msg = "no bars available for inspection window"
        raise ValidationError(msg)

    timestamps = tuple(bar.observed_at for bar in bars)
    index_by_timestamp = {timestamp: index for index, timestamp in enumerate(timestamps)}
    signal_index = index_by_timestamp.get(detected_at)
    if signal_index is None:
        msg = f"detected_at not found in bar window: {detected_at.isoformat()}"
        raise ValidationError(msg)

    horizon_end_index = signal_index + horizon_bars
    horizon_end_timestamp = (
        timestamps[horizon_end_index] if horizon_end_index < len(timestamps) else None
    )
    window_start = max(0, signal_index - padding_bars)
    if horizon_end_index < len(bars):
        window_end = min(len(bars), horizon_end_index + padding_bars + 1)
    else:
        window_end = min(len(bars), signal_index + padding_bars + 1)
    slice_bars = bars[window_start:window_end]
    sliced_timestamps = tuple(bar.observed_at for bar in slice_bars)
    sliced_index = {timestamp: index for index, timestamp in enumerate(sliced_timestamps)}

    return InspectionWindow(
        timestamps=sliced_timestamps,
        opens=tuple(float(bar.open.value) for bar in slice_bars),
        highs=tuple(float(bar.high.value) for bar in slice_bars),
        lows=tuple(float(bar.low.value) for bar in slice_bars),
        closes=tuple(float(bar.close.value) for bar in slice_bars),
        signal_index=sliced_index[detected_at],
        horizon_end_index=(
            sliced_index.get(horizon_end_timestamp) if horizon_end_timestamp is not None else None
        ),
        horizon_end_timestamp=horizon_end_timestamp,
    )


def query_window_range(
    *,
    detected_at: datetime,
    horizon_bars: int,
    padding_bars: int,
    bar_step: timedelta,
) -> tuple[datetime, datetime]:
    """Return start/end timestamps for a historical bar query."""
    start = detected_at - bar_step * padding_bars
    end = detected_at + bar_step * (horizon_bars + padding_bars)
    return start, end


def excursion_price_levels(
    *,
    reference_price: float,
    direction: str,
    mfe: float | None,
    mae: float | None,
) -> tuple[float | None, float | None]:
    """Convert signed MFE/MAE returns to absolute price levels."""
    if not math.isfinite(reference_price):
        return None, None
    mfe_level = None
    mae_level = None
    if mfe is not None and math.isfinite(mfe):
        if direction == SignalDirection.SHORT.value:
            mfe_level = reference_price * (1.0 - mfe)
        else:
            mfe_level = reference_price * (1.0 + mfe)
    if mae is not None and math.isfinite(mae):
        if direction == SignalDirection.SHORT.value:
            mae_level = reference_price * (1.0 - mae)
        else:
            mae_level = reference_price * (1.0 + mae)
    return mfe_level, mae_level


def is_complete_outcome(selection: InspectionSelection) -> bool:
    """Return True when the selected outcome row is complete."""
    return selection.outcome_status == OutcomeStatus.COMPLETE.value
