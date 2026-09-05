"""Labelled feature-matrix builder over an existing AnalysisFrame (D-S039-07/08)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import assert_never

import numpy as np
import numpy.typing as npt
import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.research.outcomes.calculator import compute_forward_outcomes_for_horizons
from trading_framework.research.outcomes.definition import (
    ForwardOutcomeDefinition,
    OutcomeStatus,
)
from trading_framework.research.predictive.errors import PredictiveMatrixError
from trading_framework.research.predictive.exclusions import MatrixExclusionCounts
from trading_framework.research.predictive.features import (
    FeatureMatrixSpec,
    FeatureSpec,
    FeatureTransform,
)
from trading_framework.research.predictive.labels import LabelKind, LabelSpec

# Matches SignalDirection.LONG without importing signal_model (ADR-0023).
_LONG_DIRECTION = "long"
_REQUIRED_OHLCV = ("high", "low", "close")


@dataclass(frozen=True, slots=True)
class LabelledFeatureMatrix:
    """Complete labelled rows plus exclusion counts. No fold-role columns.

    ``candidates`` is the full evaluation-grid frame *before* the completeness
    filter (one row per bar, long-direction outcome): ``entity_id``,
    ``label_end_at``, feature columns, ``outcome_status`` and
    ``features_finite`` are all present for every bar, labelled or not. It
    exists so a sample resolver (``application/predictive_research/``,
    S056-T004) can attribute a resolved-but-dropped row to the exact reason it
    was excluded, and so it can read ``label_end_at`` for a specific bar
    without re-deriving it from a filtered sequence (D-S056-05: filter-late).
    """

    rows: pl.DataFrame
    exclusions: MatrixExclusionCounts
    candidates: pl.DataFrame


def build_labelled_feature_matrix(
    *,
    frame: AnalysisFrame,
    ohlcv: Mapping[str, tuple[float, ...]],
    features: FeatureMatrixSpec,
    label: LabelSpec,
    horizon_bars: int,
    available_at: tuple[datetime, ...] | None = None,
) -> LabelledFeatureMatrix:
    """Build one labelled row per complete evaluation bar.

    Feature values are read from ``frame``; this function never recomputes
    analysis. Labels reuse ``compute_forward_outcomes_for_horizons`` on a
    synthetic long-only occurrence table (one row per bar). Incomplete and
    non-finite rows are excluded and counted, not labelled.
    """
    if horizon_bars < 1:
        msg = "horizon_bars must be at least 1"
        raise PredictiveMatrixError(msg)

    timestamps = frame.timestamps
    bar_count = len(timestamps)
    aliases = tuple(feature.alias for feature in features.features)
    schema = _labelled_schema(aliases)
    if bar_count == 0:
        return LabelledFeatureMatrix(
            rows=pl.DataFrame(schema=schema),
            exclusions=MatrixExclusionCounts(
                candidate_rows=0,
                labelled_rows=0,
                incomplete_horizon=0,
                insufficient_data=0,
                null_features=0,
            ),
            candidates=pl.DataFrame(schema=_candidate_schema(aliases)),
        )

    materialized_ohlcv = _require_aligned_ohlcv(ohlcv, bar_count=bar_count)
    resolved_available_at = _resolve_available_at(timestamps, available_at)
    feature_values = {
        feature.alias: _apply_transform(
            _resolve_feature_values(frame, feature),
            feature.transform,
        )
        for feature in features.features
    }
    entity_ids = [_bar_entity_id(timestamp) for timestamp in timestamps]
    outcomes = compute_forward_outcomes_for_horizons(
        _synthetic_occurrences(
            entity_ids=entity_ids,
            timestamps=timestamps,
            close=materialized_ohlcv["close"],
        ),
        frame=frame,
        ohlcv=materialized_ohlcv,
        horizons=(horizon_bars,),
        definition=ForwardOutcomeDefinition(horizon_bars=horizon_bars),
    )
    candidates = _candidate_frame(
        entity_ids=entity_ids,
        timestamps=timestamps,
        available_at=resolved_available_at,
        horizon_bars=horizon_bars,
        feature_values=feature_values,
        outcomes=outcomes,
    )
    return _select_labelled_rows(candidates, features=features, label=label, schema=schema)


def _labelled_schema(aliases: tuple[str, ...]) -> dict[str, pl.DataType]:
    utc_datetime = pl.Datetime(time_unit="us", time_zone="UTC")
    schema: dict[str, pl.DataType] = {
        "entity_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "detected_at": utc_datetime,
        "available_at": utc_datetime,
        "label_end_at": utc_datetime,
    }
    for alias in aliases:
        schema[alias] = pl.Float64()
    schema["label"] = pl.Float64()
    schema["forward_return"] = pl.Float64()
    schema["outcome_status"] = pl.String()
    return schema


def _candidate_schema(aliases: tuple[str, ...]) -> dict[str, pl.DataType]:
    """Schema of the full-grid ``candidates`` frame: no ``label``, plus a finiteness flag."""
    schema = _labelled_schema(aliases)
    del schema["label"]
    schema["features_finite"] = pl.Boolean()
    return schema


def _require_aligned_ohlcv(
    ohlcv: Mapping[str, tuple[float, ...]],
    *,
    bar_count: int,
) -> dict[str, tuple[float, ...]]:
    missing = [name for name in _REQUIRED_OHLCV if name not in ohlcv]
    if missing:
        msg = f"ohlcv columns missing required field: {missing[0]}"
        raise PredictiveMatrixError(msg)
    materialized = {name: tuple(values) for name, values in ohlcv.items()}
    for name, values in materialized.items():
        if len(values) != bar_count:
            msg = f"ohlcv column {name!r} length must match frame timestamps"
            raise PredictiveMatrixError(msg)
    return materialized


def _resolve_available_at(
    timestamps: tuple[datetime, ...],
    available_at: tuple[datetime, ...] | None,
) -> tuple[datetime, ...]:
    if available_at is None:
        return timestamps
    if len(available_at) != len(timestamps):
        msg = "available_at length must match frame timestamps"
        raise PredictiveMatrixError(msg)
    for detected_at, feature_available_at in zip(timestamps, available_at, strict=True):
        if feature_available_at > detected_at:
            msg = "feature available_at must not be later than detected_at"
            raise PredictiveMatrixError(msg)
    return available_at


def _resolve_feature_values(frame: AnalysisFrame, feature: FeatureSpec) -> npt.NDArray[np.float64]:
    column_name = _resolve_feature_column(frame, feature)
    values = frame.columns[column_name]
    if len(values) != len(frame.timestamps):
        msg = f"feature column {feature.alias!r} length must match frame timestamps"
        raise PredictiveMatrixError(msg)
    return np.asarray(values, dtype=np.float64)


def _resolve_feature_column(frame: AnalysisFrame, feature: FeatureSpec) -> str:
    if feature.alias in frame.columns:
        return feature.alias
    for column_name, output_ref in frame.column_lineage.items():
        identity = output_ref.computation_identity
        if (
            output_ref.output_id == feature.output_id
            and identity.component_id == feature.component_id
            and identity.parameters == feature.parameters
            and column_name in frame.columns
        ):
            return column_name
    msg = f"declared feature alias is not present on the analysis frame: {feature.alias!r}"
    raise PredictiveMatrixError(msg)


def _apply_transform(
    values: npt.NDArray[np.float64],
    transform: FeatureTransform,
) -> npt.NDArray[np.float64]:
    if transform is FeatureTransform.NONE:
        return np.array(values, dtype=np.float64, copy=True)
    if transform is FeatureTransform.LOG:
        return _log_transform(values)
    if transform is FeatureTransform.DIFF:
        return _backward_diff(values)
    if transform is FeatureTransform.PCT_CHANGE:
        return _backward_pct_change(values)
    if transform is FeatureTransform.RANK:
        msg = (
            "RANK transform is not supported in this matrix slice; "
            "cross-sectional versus expanding rank is ambiguous and a global rank would leak"
        )
        raise PredictiveMatrixError(msg)
    assert_never(transform)


def _log_transform(values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    out = np.full(values.shape, np.nan, dtype=np.float64)
    valid = np.isfinite(values) & (values > 0.0)
    out[valid] = np.log(values[valid])
    return out


def _backward_diff(values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """``DIFF[t]`` uses ``t`` and ``t-1`` only; the first bar is non-finite."""
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < 2:
        return out
    current = values[1:]
    previous = values[:-1]
    valid = np.isfinite(current) & np.isfinite(previous)
    out[1:] = np.where(valid, current - previous, np.nan)
    return out


def _backward_pct_change(values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """``PCT_CHANGE[t]`` uses ``t`` and ``t-1`` only; the first bar is non-finite."""
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < 2:
        return out
    current = values[1:]
    previous = values[:-1]
    valid = np.isfinite(current) & np.isfinite(previous) & (previous != 0.0)
    out[1:] = np.where(valid, (current - previous) / previous, np.nan)
    return out


def _bar_entity_id(timestamp: datetime) -> str:
    if timestamp.tzinfo is None:
        msg = "frame timestamps must be timezone-aware UTC"
        raise PredictiveMatrixError(msg)
    return timestamp.astimezone(UTC).isoformat()


def _synthetic_occurrences(
    *,
    entity_ids: list[str],
    timestamps: tuple[datetime, ...],
    close: tuple[float, ...],
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "occurrence_id": entity_ids,
            "detected_at": list(timestamps),
            "reference_price": list(close),
            "direction": [_LONG_DIRECTION] * len(entity_ids),
        }
    )


def _candidate_frame(
    *,
    entity_ids: list[str],
    timestamps: tuple[datetime, ...],
    available_at: tuple[datetime, ...],
    horizon_bars: int,
    feature_values: Mapping[str, npt.NDArray[np.float64]],
    outcomes: pl.DataFrame,
) -> pl.DataFrame:
    bar_count = len(timestamps)
    payload: dict[str, object] = {
        "entity_id": entity_ids,
        "horizon_bars": [horizon_bars] * bar_count,
        "detected_at": list(timestamps),
        "available_at": list(available_at),
        "label_end_at": _label_end_timestamps(timestamps, horizon_bars),
    }
    for alias, values in feature_values.items():
        payload[alias] = values.tolist()
    candidates = pl.DataFrame(payload)
    return candidates.join(
        outcomes.select("occurrence_id", "outcome_status", "forward_return"),
        left_on="entity_id",
        right_on="occurrence_id",
        how="left",
    )


def _label_end_timestamps(
    timestamps: tuple[datetime, ...],
    horizon_bars: int,
) -> list[datetime | None]:
    bar_count = len(timestamps)
    ends: list[datetime | None] = []
    for index in range(bar_count):
        end_index = index + horizon_bars
        if end_index >= bar_count:
            ends.append(None)
        else:
            ends.append(timestamps[end_index])
    return ends


def _select_labelled_rows(
    candidates: pl.DataFrame,
    *,
    features: FeatureMatrixSpec,
    label: LabelSpec,
    schema: dict[str, pl.DataType],
) -> LabelledFeatureMatrix:
    aliases = tuple(feature.alias for feature in features.features)
    feature_finite = pl.all_horizontal(
        *(pl.col(alias).is_not_null() & pl.col(alias).is_finite() for alias in aliases)
    )
    complete = pl.col("outcome_status") == OutcomeStatus.COMPLETE.value
    incomplete = pl.col("outcome_status") == OutcomeStatus.INCOMPLETE_HORIZON.value
    insufficient = (pl.col("outcome_status") == OutcomeStatus.INSUFFICIENT_DATA.value) | pl.col(
        "outcome_status"
    ).is_null()

    exclusions = MatrixExclusionCounts(
        candidate_rows=len(candidates),
        labelled_rows=candidates.filter(complete & feature_finite).height,
        incomplete_horizon=candidates.filter(incomplete).height,
        insufficient_data=candidates.filter(insufficient).height,
        null_features=candidates.filter(complete & feature_finite.not_()).height,
    )
    labelled = candidates.filter(complete & feature_finite).with_columns(
        label_expr(label).alias("label")
    )
    rows = pl.DataFrame(schema=schema) if labelled.height == 0 else labelled.select(list(schema))
    annotated_candidates = candidates.with_columns(feature_finite.alias("features_finite"))
    return LabelledFeatureMatrix(rows=rows, exclusions=exclusions, candidates=annotated_candidates)


def label_expr(spec: LabelSpec) -> pl.Expr:
    """Label expression from a ``forward_return`` column (public: reused by S056-T004's
    signal_occurrences resolver so a recomputed, direction-adjusted ``forward_return``
    is mapped to ``label`` with the exact same rule ``every_bar`` uses)."""
    forward_return = pl.col("forward_return")
    if spec.kind is LabelKind.REGRESSION:
        return forward_return
    if spec.kind is LabelKind.BINARY:
        threshold = spec.threshold
        if threshold is None:
            msg = "BINARY label requires threshold"
            raise PredictiveMatrixError(msg)
        return pl.when(forward_return > threshold).then(1.0).otherwise(0.0)
    if spec.kind is LabelKind.TERNARY:
        band = spec.neutral_band
        if band is None:
            msg = "TERNARY label requires neutral_band"
            raise PredictiveMatrixError(msg)
        return (
            pl.when(forward_return.abs() <= band)
            .then(0.0)
            .when(forward_return > 0.0)
            .then(1.0)
            .otherwise(-1.0)
        )
    assert_never(spec.kind)
