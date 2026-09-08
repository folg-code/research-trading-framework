"""Resolve a ``signal_occurrences`` sample into real, provenance-carrying rows (S056-T004).

Layering (ADR-0031 Decision 3, D-S056-04): ``research/predictive/`` DECLARES
(``SampleSpec`` is pure data and accepts an already-resolved row selection);
this module RESOLVES. It is the one place in Predictive Research allowed to
import ``evaluate_models`` and ``materialize_signal_occurrences`` -- the same
functions Signal Research calls, reused unchanged, never forked.

Filter-late (D-S056-05, the sprint's central leakage lock): the full
evaluation grid is labelled FIRST via the unmodified
``build_labelled_feature_matrix`` -- features, ``label_end_at`` and outcome
status are all computed positionally over the *complete* grid, exactly as
``every_bar`` computes them. Only *after* that full-grid frame exists does
this module select the subset of already-labelled bars whose timestamp
matches a resolved Signal Model occurrence. No sample selection happens
before ``label_end_at`` is derived; the code has no path that could compute
it against an already-filtered sequence, because the full-grid frame the
resolver reads from was never filtered to begin with.

Direction passthrough (D-S056-06): the occurrence's own ``direction`` is used
to recompute ``forward_return`` (and, from it, ``label``) for the resolved
subset by calling ``compute_forward_outcomes_for_horizons`` a second time,
scoped to just the kept occurrences -- the same function ``every_bar`` used
for its (direction-agnostic, long-only) first pass, and the same function
Signal Research itself uses. No bespoke outcome logic is written. The
occurrence's own ``entity_id`` (``derive_occurrence_id``'s output) replaces
the bar-timestamp ``entity_id`` on every kept row.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.outcomes.calculator import compute_forward_outcomes_for_horizons
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition, OutcomeStatus
from trading_framework.research.predictive.errors import PredictiveMatrixError
from trading_framework.research.predictive.exclusions import MatrixExclusionCounts
from trading_framework.research.predictive.labels import LabelSpec
from trading_framework.research.predictive.matrix import LabelledFeatureMatrix, label_expr
from trading_framework.research.predictive.sample import SampleDirection, SampleSpec
from trading_framework.signal_model.definitions import SignalDirection, SignalModelDefinition
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    materialize_signal_occurrences,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver

# Exclusion reasons match MatrixExclusionCounts' vocabulary (Finding 5): a
# signal_occurrences drop is described with the same three named reasons
# every_bar already uses, not a bespoke taxonomy.
_REASON_INCOMPLETE_HORIZON = "incomplete_horizon"
_REASON_INSUFFICIENT_DATA = "insufficient_data"
_REASON_NULL_FEATURES = "null_features"

_DIRECTION_TO_SIGNAL_DIRECTION: dict[SampleDirection, SignalDirection] = {
    SampleDirection.LONG: SignalDirection.LONG,
    SampleDirection.SHORT: SignalDirection.SHORT,
}

# Occurrence-table columns plus the full-grid columns joined onto them that
# are NOT declared feature columns (D-S056-06's rewritten fields, and the
# bookkeeping columns this module adds).
_KEPT_NON_FEATURE_COLUMNS = frozenset(
    {
        "occurrence_id",
        "signal_model_id",
        "detected_at",
        "available_at",
        "direction",
        "reference_price",
        "instrument",
        "evaluation_timeframe",
        "source_dataset_ref",
        "label_end_at",
        "outcome_status",
        "features_finite",
        "_reason",
    }
)


class SignalOccurrenceResolutionError(PredictiveMatrixError):
    """Raised when a ``signal_occurrences`` sample cannot be resolved to rows."""


@dataclass(frozen=True, slots=True)
class ResolvedSignalOccurrenceSample:
    """A ``signal_occurrences`` sample resolved to real, labelled rows.

    ``rows`` has the exact schema ``build_labelled_feature_matrix`` produces
    for ``every_bar`` (so it flows into ``assign_purged_walk_forward_folds``
    and the dataset repository unchanged), except ``entity_id`` carries the
    occurrence's own id (D-S056-06), not a bar timestamp.
    """

    rows: pl.DataFrame
    exclusion_counts: MatrixExclusionCounts
    occurrences: pl.DataFrame


def resolve_signal_occurrences_sample(
    *,
    sample: SampleSpec,
    signal_model: SignalModelDefinition,
    dataset_ref: DatasetRef,
    timeframe: Timeframe,
    requested_range: TimeRange,
    evaluation_timeframe: Timeframe,
    storage_root: Path,
    horizon_bars: int,
    label: LabelSpec,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    full_grid: LabelledFeatureMatrix,
    session_resolver: TradingSessionResolver | None = None,
    preloaded_bars: tuple[MarketBar, ...] | None = None,
    preloaded_column_batch: OhlcvColumnBatch | None = None,
    preloaded_view: AnalysisDataView | None = None,
) -> ResolvedSignalOccurrenceSample:
    """Resolve ``sample`` (kind ``signal_occurrences``) against ``signal_model``.

    ``frame``/``ohlcv``/``full_grid`` are the SAME full-evaluation-grid inputs
    the ``every_bar`` path already builds (D-S056-05: computed once, before
    any sample selection). ``evaluate_models`` runs a *separate* analysis pass
    scoped to ``signal_model``'s own dependencies purely to obtain emissions;
    it never supplies the feature/label values used below, which always come
    from ``full_grid`` (the frame this study's own declared features were
    computed against).
    """
    if signal_model.signal_model_id != sample.signal_model_id:
        msg = (
            "resolved signal model id does not match the declared sample: "
            f"{signal_model.signal_model_id!r} != {sample.signal_model_id!r}"
        )
        raise SignalOccurrenceResolutionError(msg)

    eval_result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=timeframe,
            requested_range=requested_range,
            storage_root=storage_root,
            signal_models=(signal_model,),
            evaluation_timeframe=evaluation_timeframe,
            session_resolver=session_resolver,
            preloaded_bars=preloaded_bars,
            preloaded_column_batch=preloaded_column_batch,
            preloaded_view=preloaded_view,
        )
    )
    emission_frame = eval_result.analysis.frame
    if emission_frame is None:
        msg = "signal_occurrences resolution requires an assembled AnalysisFrame"
        raise SignalOccurrenceResolutionError(msg)

    emissions = eval_result.signal_model_emissions[signal_model.signal_model_id]
    occurrences = materialize_signal_occurrences(
        emissions,
        frame=emission_frame,
        market_view=eval_result.analysis.workspace.market_view,
        context=OccurrenceMaterializationContext(
            signal_model_id=signal_model.signal_model_id,
            instrument=dataset_ref.dataset_id.instrument_id.value,
            evaluation_timeframe=evaluation_timeframe,
            source_dataset_ref=str(dataset_ref),
        ),
    )
    occurrences = _filter_by_direction(occurrences, sample.direction)
    return _resolve_from_occurrences(
        occurrences,
        horizon_bars=horizon_bars,
        label=label,
        frame=frame,
        ohlcv=ohlcv,
        full_grid=full_grid,
    )


def _filter_by_direction(occurrences: pl.DataFrame, direction: SampleDirection) -> pl.DataFrame:
    """Filter, never rewrite, occurrence direction (D-S056-06)."""
    if direction is SampleDirection.ANY or occurrences.height == 0:
        return occurrences
    signal_direction = _DIRECTION_TO_SIGNAL_DIRECTION[direction]
    return occurrences.filter(pl.col("direction") == signal_direction.value)


def _resolve_from_occurrences(
    occurrences: pl.DataFrame,
    *,
    horizon_bars: int,
    label: LabelSpec,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    full_grid: LabelledFeatureMatrix,
) -> ResolvedSignalOccurrenceSample:
    universe_row_count = occurrences.height
    if universe_row_count == 0:
        empty_rows = pl.DataFrame(schema=full_grid.rows.schema)
        return ResolvedSignalOccurrenceSample(
            rows=empty_rows,
            exclusion_counts=MatrixExclusionCounts(
                candidate_rows=0,
                labelled_rows=0,
                incomplete_horizon=0,
                insufficient_data=0,
                null_features=0,
            ),
            occurrences=occurrences,
        )

    # Take label_end_at, outcome_status, features_finite AND every declared
    # feature column from the full-grid candidates -- everything except the
    # bar-based entity_id/horizon_bars/available_at/forward_return, which the
    # occurrence's own values (entity_id, direction-adjusted forward_return)
    # or a shared constant (horizon_bars/available_at) replace below.
    _from_full_grid = {"entity_id", "horizon_bars", "available_at", "forward_return"}
    candidate_columns = [
        name for name in full_grid.candidates.columns if name not in _from_full_grid
    ]
    joined = occurrences.join(
        full_grid.candidates.select(candidate_columns),
        on="detected_at",
        how="left",
    )

    reasons = [
        _classify_row(status, features_finite)
        for status, features_finite in zip(
            joined.get_column("outcome_status").to_list(),
            joined.get_column("features_finite").to_list(),
            strict=True,
        )
    ]
    joined = joined.with_columns(pl.Series("_reason", reasons))
    kept = joined.filter(pl.col("_reason").is_null())

    labelled_rows = _labelled_rows_from_kept(
        kept,
        horizon_bars=horizon_bars,
        label=label,
        frame=frame,
        ohlcv=ohlcv,
        schema=full_grid.rows.schema,
    )
    reason_counts = Counter(reason for reason in reasons if reason is not None)
    exclusion_counts = MatrixExclusionCounts(
        candidate_rows=universe_row_count,
        labelled_rows=labelled_rows.height,
        incomplete_horizon=reason_counts.get(_REASON_INCOMPLETE_HORIZON, 0),
        insufficient_data=reason_counts.get(_REASON_INSUFFICIENT_DATA, 0),
        null_features=reason_counts.get(_REASON_NULL_FEATURES, 0),
    )
    return ResolvedSignalOccurrenceSample(
        rows=labelled_rows,
        exclusion_counts=exclusion_counts,
        occurrences=occurrences,
    )


def _classify_row(status: str | None, features_finite: bool | None) -> str | None:
    """Return the drop reason for one occurrence, or ``None`` if it is kept.

    An occurrence whose ``detected_at`` is absent from the full evaluation
    grid (``status is None``, e.g. a bar the grid never observed) is
    classified ``insufficient_data``: no data was available to label it,
    which is exactly what that reason already means for ``every_bar``.
    """
    if status == OutcomeStatus.INCOMPLETE_HORIZON.value:
        return _REASON_INCOMPLETE_HORIZON
    if status == OutcomeStatus.COMPLETE.value:
        return None if features_finite else _REASON_NULL_FEATURES
    return _REASON_INSUFFICIENT_DATA


def _labelled_rows_from_kept(
    kept: pl.DataFrame,
    *,
    horizon_bars: int,
    label: LabelSpec,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    schema: pl.Schema,
) -> pl.DataFrame:
    if kept.height == 0:
        return pl.DataFrame(schema=schema)

    # Recompute forward_return/outcome_status with the occurrence's OWN
    # direction (D-S056-06) -- the same function every_bar already used for
    # its long-only first pass, and the same function Signal Research uses.
    # This is a second pass scoped to the resolved subset only; label_end_at
    # above was already read from the full-grid frame, never re-derived here.
    outcomes = compute_forward_outcomes_for_horizons(
        kept.select("occurrence_id", "detected_at", "reference_price", "direction"),
        frame=frame,
        ohlcv=ohlcv,
        horizons=(horizon_bars,),
        definition=ForwardOutcomeDefinition(horizon_bars=horizon_bars),
    )
    rows = kept.select(
        pl.col("occurrence_id").alias("entity_id"),
        pl.lit(horizon_bars, dtype=pl.Int64).alias("horizon_bars"),
        pl.col("detected_at"),
        # available_at == detected_at, matching every_bar's own convention
        # (matrix.py's build_labelled_feature_matrix defaults available_at to
        # the bar timestamp itself when no override is passed). This is
        # deliberately NOT the occurrence's own materialize_signal_occurrences
        # available_at column, which -- like MarketBar.available_at -- may
        # carry a data-latency lag; conflating the two would mix two
        # different "availability" concepts on the same column (see this
        # package's CLAUDE.md: "this is not MarketBar.available_at").
        pl.col("detected_at").alias("available_at"),
        pl.col("label_end_at"),
    ).join(
        outcomes.select("occurrence_id", "outcome_status", "forward_return").rename(
            {"occurrence_id": "entity_id"}
        ),
        on="entity_id",
        how="inner",
    )
    feature_columns = [name for name in kept.columns if name not in _KEPT_NON_FEATURE_COLUMNS]
    features = kept.select("occurrence_id", *feature_columns).rename({"occurrence_id": "entity_id"})
    rows = rows.join(features, on="entity_id", how="inner").with_columns(
        label_expr(label).alias("label")
    )
    return rows.select(list(schema))


__all__ = [
    "ResolvedSignalOccurrenceSample",
    "SignalOccurrenceResolutionError",
    "resolve_signal_occurrences_sample",
]
