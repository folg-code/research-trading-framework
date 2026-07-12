"""Run Signal Research — evaluate signals, materialize occurrences, compute outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.signal_research import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    derive_run_id,
    outcome_definition_fingerprint,
)
from trading_framework.research.outcomes import (
    ForwardOutcomeDefinition,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes_for_horizons,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    materialize_signal_occurrences,
)
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class SignalResearchError(ValidationError):
    """Raised when Signal Research orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunSignalResearchRequest:
    """Input for one Signal Research run."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    signal_models: tuple[SignalModelDefinition, ...]
    horizons: tuple[int, ...]
    evaluation_timeframe: Timeframe | None = None
    session_resolver: TradingSessionResolver | None = None
    outcome_definition: ForwardOutcomeDefinition | None = None
    experiment_id: str | None = None
    persist: bool = True


@dataclass(frozen=True, slots=True)
class RunSignalResearchResult:
    """Outcome of one Signal Research run."""

    run_id: str
    run_ref: RunDatasetRef
    occurrences: pl.DataFrame
    outcomes: pl.DataFrame
    manifest: SignalResearchRunManifest


def run_signal_research(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None = None,
) -> RunSignalResearchResult:
    """Evaluate signal models, compute forward outcomes, and optionally persist the run."""
    if not request.signal_models:
        msg = "signal_models must contain at least one SignalModelDefinition"
        raise SignalResearchError(msg)
    if not request.horizons:
        msg = "horizons must contain at least one horizon"
        raise SignalResearchError(msg)

    evaluation_timeframe = request.evaluation_timeframe or request.timeframe
    eval_result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=request.requested_range,
            storage_root=request.storage_root,
            signal_models=request.signal_models,
            evaluation_timeframe=evaluation_timeframe,
            session_resolver=request.session_resolver,
        )
    )
    frame = eval_result.analysis.frame
    if frame is None:
        msg = "signal research requires an assembled AnalysisFrame"
        raise SignalResearchError(msg)

    market_view = eval_result.analysis.workspace.market_view
    ohlcv = align_ohlcv_to_evaluation_frame(frame, market_view)
    source_dataset_ref = str(request.dataset_ref)
    instrument = request.dataset_ref.dataset_id.instrument_id.value

    occurrence_frames: list[pl.DataFrame] = []
    for signal_model in request.signal_models:
        emissions = eval_result.signal_model_emissions[signal_model.signal_model_id]
        occurrence_frames.append(
            materialize_signal_occurrences(
                emissions,
                frame=frame,
                market_view=market_view,
                context=OccurrenceMaterializationContext(
                    signal_model_id=signal_model.signal_model_id,
                    instrument=instrument,
                    evaluation_timeframe=evaluation_timeframe,
                    source_dataset_ref=source_dataset_ref,
                ),
            )
        )
    occurrences = (
        pl.concat(occurrence_frames) if occurrence_frames else empty_signal_occurrences_dataframe()
    )

    outcomes = compute_forward_outcomes_for_horizons(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        horizons=request.horizons,
        definition=request.outcome_definition,
    )

    signal_model_ids = tuple(model.signal_model_id for model in request.signal_models)
    definition_fingerprint = outcome_definition_fingerprint(
        request.horizons,
        request.outcome_definition,
    )
    run_id = derive_run_id(
        source_dataset_ref=source_dataset_ref,
        signal_model_ids=signal_model_ids,
        horizons=request.horizons,
        evaluation_timeframe=evaluation_timeframe.value,
        requested_range_start=request.requested_range.start,
        requested_range_end=request.requested_range.end,
        framework_version=framework_version,
        outcome_definition_fingerprint=definition_fingerprint,
    )
    manifest = SignalResearchRunManifest(
        run_id=run_id,
        schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        source_dataset_ref=source_dataset_ref,
        evaluation_timeframe=evaluation_timeframe.value,
        signal_model_ids=signal_model_ids,
        horizon_bars_requested=request.horizons,
        reference_price_policy=(
            request.outcome_definition.reference_price_policy
            if request.outcome_definition is not None
            else ForwardOutcomeDefinition(horizon_bars=request.horizons[0]).reference_price_policy
        ),
        outcome_definition_fingerprint=definition_fingerprint,
        experiment_id=request.experiment_id,
    )
    envelope = SignalResearchRunEnvelope(
        manifest=manifest,
        occurrences=occurrences,
        outcomes=outcomes,
    )
    run_ref = RunDatasetRef(run_id=run_id)
    if request.persist:
        repo = repository or SignalResearchDatasetRepository(request.storage_root)
        run_ref = repo.write(envelope)

    return RunSignalResearchResult(
        run_id=run_id,
        run_ref=run_ref,
        occurrences=occurrences,
        outcomes=outcomes,
        manifest=manifest,
    )
