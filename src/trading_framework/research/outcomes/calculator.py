"""Forward outcome calculator — long-format outcome facts from occurrences."""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import numpy.typing as npt
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

_STATUS_COMPLETE = 0
_STATUS_INCOMPLETE = 1
_STATUS_INSUFFICIENT = 2
_STATUS_OMIT = 3

_DIR_LONG = 1
_DIR_SHORT = -1


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


def _ohlcv_array(
    ohlcv: dict[str, tuple[float, ...]],
    field: MarketField,
) -> npt.NDArray[np.float64]:
    key = field.value
    if key not in ohlcv:
        msg = f"ohlcv columns missing required field: {key}"
        raise KeyError(msg)
    return np.ascontiguousarray(ohlcv[key], dtype=np.float64)


def _direction_codes(directions: list[str]) -> npt.NDArray[np.int8]:
    codes = np.empty(len(directions), dtype=np.int8)
    for index, direction in enumerate(directions):
        codes[index] = _DIR_SHORT if direction == SignalDirection.SHORT.value else _DIR_LONG
    return codes


def _signal_indices(
    detected_at_values: list[datetime],
    index_by_timestamp: dict[datetime, int],
) -> npt.NDArray[np.int64]:
    indices = np.full(len(detected_at_values), -1, dtype=np.int64)
    for index, detected_at in enumerate(detected_at_values):
        resolved = index_by_timestamp.get(detected_at)
        if resolved is not None:
            indices[index] = resolved
    return indices


def _compute_forward_outcome_arrays(
    *,
    signal_index: npt.NDArray[np.int64],
    reference_price: npt.NDArray[np.float64],
    direction: npt.NDArray[np.int8],
    high: npt.NDArray[np.float64],
    low: npt.NDArray[np.float64],
    close: npt.NDArray[np.float64],
    terminal: npt.NDArray[np.float64],
    horizon: int,
    emit_incomplete: bool,
) -> tuple[
    npt.NDArray[np.int8],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]:
    """Compute forward outcomes for one horizon on contiguous OHLCV arrays."""
    occurrence_count = int(signal_index.shape[0])
    bar_count = int(high.shape[0])
    status = np.full(occurrence_count, _STATUS_OMIT, dtype=np.int8)
    terminal_price = np.full(occurrence_count, np.nan, dtype=np.float64)
    forward_return = np.full(occurrence_count, np.nan, dtype=np.float64)
    mfe = np.full(occurrence_count, np.nan, dtype=np.float64)
    mae = np.full(occurrence_count, np.nan, dtype=np.float64)

    for occurrence_index in range(occurrence_count):
        bar_index = int(signal_index[occurrence_index])
        price = float(reference_price[occurrence_index])
        if bar_index < 0 or not math.isfinite(price):
            status[occurrence_index] = _STATUS_INSUFFICIENT
            continue

        window_start = bar_index + 1
        window_end = bar_index + horizon
        if window_end >= bar_count:
            if emit_incomplete:
                status[occurrence_index] = _STATUS_INCOMPLETE
            continue

        window_high = high[window_start : window_end + 1]
        window_low = low[window_start : window_end + 1]
        window_terminal = terminal[window_start : window_end + 1]
        window_close = close[window_start : window_end + 1]
        if not (
            np.isfinite(window_high).all()
            and np.isfinite(window_low).all()
            and np.isfinite(window_terminal).all()
            and np.isfinite(window_close).all()
        ):
            status[occurrence_index] = _STATUS_INSUFFICIENT
            continue

        end_price = float(terminal[window_end])
        raw_return = end_price / price - 1.0
        direction_code = int(direction[occurrence_index])
        signed_return = -raw_return if direction_code == _DIR_SHORT else raw_return

        status[occurrence_index] = _STATUS_COMPLETE
        terminal_price[occurrence_index] = end_price
        forward_return[occurrence_index] = signed_return

        if price == 0.0:
            continue

        high_returns = window_high / price - 1.0
        low_returns = window_low / price - 1.0
        if direction_code == _DIR_SHORT:
            favorable = -low_returns
            adverse = -high_returns
        else:
            favorable = high_returns
            adverse = low_returns

        mfe[occurrence_index] = max(float(favorable.max()), 0.0)
        mae[occurrence_index] = min(float(adverse.min()), 0.0)

    return status, terminal_price, forward_return, mfe, mae


def _status_label(code: int) -> str:
    if code == _STATUS_COMPLETE:
        return OutcomeStatus.COMPLETE.value
    if code == _STATUS_INCOMPLETE:
        return OutcomeStatus.INCOMPLETE_HORIZON.value
    return OutcomeStatus.INSUFFICIENT_DATA.value


def _metric_or_null(value: float, *, include: bool) -> float | None:
    if not include:
        return None
    return value


def _outcomes_dataframe(
    *,
    occurrence_ids: list[str],
    horizon: int,
    status: npt.NDArray[np.int8],
    terminal_price: npt.NDArray[np.float64],
    forward_return: npt.NDArray[np.float64],
    mfe: npt.NDArray[np.float64],
    mae: npt.NDArray[np.float64],
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for index, occurrence_id in enumerate(occurrence_ids):
        code = int(status[index])
        if code == _STATUS_OMIT:
            continue
        complete = code == _STATUS_COMPLETE
        rows.append(
            {
                "occurrence_id": occurrence_id,
                "horizon_bars": horizon,
                "outcome_status": _status_label(code),
                "terminal_price": _metric_or_null(float(terminal_price[index]), include=complete),
                "forward_return": _metric_or_null(float(forward_return[index]), include=complete),
                "mfe": _metric_or_null(float(mfe[index]), include=complete),
                "mae": _metric_or_null(float(mae[index]), include=complete),
            }
        )
    if not rows:
        return empty_forward_outcomes_dataframe()
    return pl.DataFrame(rows, schema=_outcome_schema())


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

    return compute_forward_outcomes_for_horizons(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        horizons=(definition.horizon_bars,),
        definition=definition,
    )


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
    if len(occurrences) == 0:
        return empty_forward_outcomes_dataframe()

    base = definition or ForwardOutcomeDefinition(horizon_bars=horizons[0])
    emit_incomplete = base.incomplete_horizon_policy == IncompleteHorizonPolicy.EMIT_WITH_STATUS
    index_by_timestamp = timestamp_index(frame)
    close = _ohlcv_array(ohlcv, MarketField.CLOSE)
    terminal = _ohlcv_array(ohlcv, base.terminal_price_field)
    high = _ohlcv_array(ohlcv, base.excursion_high_field)
    low = _ohlcv_array(ohlcv, base.excursion_low_field)

    occurrence_ids = occurrences.get_column("occurrence_id").to_list()
    detected_at_values = occurrences.get_column("detected_at").to_list()
    reference_price = np.ascontiguousarray(
        occurrences.get_column("reference_price").to_numpy(),
        dtype=np.float64,
    )
    direction = _direction_codes(occurrences.get_column("direction").to_list())
    signal_index = _signal_indices(detected_at_values, index_by_timestamp)

    frames: list[pl.DataFrame] = []
    for horizon in horizons:
        status, terminal_price, forward_return, mfe, mae = _compute_forward_outcome_arrays(
            signal_index=signal_index,
            reference_price=reference_price,
            direction=direction,
            high=high,
            low=low,
            close=close,
            terminal=terminal,
            horizon=horizon,
            emit_incomplete=emit_incomplete,
        )
        frames.append(
            _outcomes_dataframe(
                occurrence_ids=occurrence_ids,
                horizon=horizon,
                status=status,
                terminal_price=terminal_price,
                forward_return=forward_return,
                mfe=mfe,
                mae=mae,
            )
        )
    return pl.concat(frames) if frames else empty_forward_outcomes_dataframe()
