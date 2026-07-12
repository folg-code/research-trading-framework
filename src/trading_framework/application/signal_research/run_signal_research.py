"""Run Signal Research — scope-aware evaluation, materialization, outcomes, persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import assert_never

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research.context import (
    align_context_facts_at_available_at,
    empty_context_facts_dataframe,
)
from trading_framework.research.datasets.signal_research import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    derive_run_id,
    derive_run_id_v2,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations import (
    ObservationMaterializationContext,
    empty_market_model_observations_dataframe,
    materialize_market_model_observations,
    observations_as_outcome_occurrences,
)
from trading_framework.research.outcomes import (
    ForwardOutcomeDefinition,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes_for_horizons,
)
from trading_framework.research.requests import (
    SignalResearchRequest,
    validate_signal_research_request,
)
from trading_framework.research.scope import ResearchScope
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
    """Input for one scope-aware Signal Research run."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    signal_models: tuple[SignalModelDefinition, ...]
    horizons: tuple[int, ...]
    scope: ResearchScope = ResearchScope.SIGNAL_MODEL_ONLY
    market_models: tuple[MarketModelDefinition, ...] = ()
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
    manifest: SignalResearchRunManifest
    outcomes: pl.DataFrame
    occurrences: pl.DataFrame
    observations: pl.DataFrame
    context: pl.DataFrame


def run_signal_research(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None = None,
) -> RunSignalResearchResult:
    """Evaluate models, compute forward outcomes, and optionally persist the run."""
    if not request.horizons:
        msg = "horizons must contain at least one horizon"
        raise SignalResearchError(msg)

    outcome_definition = request.outcome_definition or ForwardOutcomeDefinition(
        horizon_bars=request.horizons[0]
    )
    validate_signal_research_request(
        SignalResearchRequest(
            scope=request.scope,
            dataset_ref=request.dataset_ref,
            market_models=request.market_models,
            signal_models=request.signal_models,
            outcome_definition=outcome_definition,
        )
    )

    if request.scope is ResearchScope.MARKET_MODEL_ONLY:
        return _run_market_model_only(
            request, repository=repository, outcome_definition=outcome_definition
        )
    if request.scope is ResearchScope.SIGNAL_MODEL_ONLY:
        return _run_signal_model_only(
            request, repository=repository, outcome_definition=outcome_definition
        )
    if request.scope is ResearchScope.MARKET_AND_SIGNAL:
        return _run_market_and_signal(
            request, repository=repository, outcome_definition=outcome_definition
        )

    assert_never(request.scope)


def _run_signal_model_only(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None,
    outcome_definition: ForwardOutcomeDefinition,
) -> RunSignalResearchResult:
    if not request.signal_models:
        msg = "signal_models must contain at least one SignalModelDefinition"
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
        definition=outcome_definition,
    )

    signal_model_ids = tuple(model.signal_model_id for model in request.signal_models)
    definition_fingerprint = outcome_definition_fingerprint(request.horizons, outcome_definition)
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
        reference_price_policy=outcome_definition.reference_price_policy,
        outcome_definition_fingerprint=definition_fingerprint,
        experiment_id=request.experiment_id,
    )
    return _persist_run(
        request,
        repository=repository,
        manifest=manifest,
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        context=empty_context_facts_dataframe(),
        outcomes=outcomes,
    )


def _run_market_and_signal(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None,
    outcome_definition: ForwardOutcomeDefinition,
) -> RunSignalResearchResult:
    market_model = request.market_models[0]
    signal_model = request.signal_models[0]
    evaluation_timeframe = request.evaluation_timeframe or request.timeframe
    eval_result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=request.requested_range,
            storage_root=request.storage_root,
            market_models=(market_model,),
            signal_models=(signal_model,),
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

    emissions = eval_result.signal_model_emissions[signal_model.signal_model_id]
    occurrences = materialize_signal_occurrences(
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
    market_state = eval_result.market_model_results[market_model.market_model_id]
    context = align_context_facts_at_available_at(
        occurrences,
        market_state,
        market_model_id=market_model.market_model_id,
    )
    outcomes = compute_forward_outcomes_for_horizons(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        horizons=request.horizons,
        definition=outcome_definition,
    )

    definition_fingerprint = outcome_definition_fingerprint(request.horizons, outcome_definition)
    run_id = derive_run_id_v2(
        research_scope=ResearchScope.MARKET_AND_SIGNAL,
        source_dataset_ref=source_dataset_ref,
        market_model_ids=(market_model.market_model_id,),
        signal_model_ids=(signal_model.signal_model_id,),
        horizons=request.horizons,
        evaluation_timeframe=evaluation_timeframe.value,
        requested_range_start=request.requested_range.start,
        requested_range_end=request.requested_range.end,
        framework_version=framework_version,
        outcome_definition_fingerprint=definition_fingerprint,
    )
    manifest = SignalResearchRunManifest(
        run_id=run_id,
        schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        source_dataset_ref=source_dataset_ref,
        evaluation_timeframe=evaluation_timeframe.value,
        signal_model_ids=(signal_model.signal_model_id,),
        horizon_bars_requested=request.horizons,
        reference_price_policy=outcome_definition.reference_price_policy,
        outcome_definition_fingerprint=definition_fingerprint,
        experiment_id=request.experiment_id,
        research_scope=ResearchScope.MARKET_AND_SIGNAL,
        market_model_ids=(market_model.market_model_id,),
    )
    return _persist_run(
        request,
        repository=repository,
        manifest=manifest,
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        context=context,
        outcomes=outcomes,
    )


def _run_market_model_only(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None,
    outcome_definition: ForwardOutcomeDefinition,
) -> RunSignalResearchResult:
    market_model = request.market_models[0]
    evaluation_timeframe = request.evaluation_timeframe or request.timeframe
    eval_result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=request.requested_range,
            storage_root=request.storage_root,
            market_models=(market_model,),
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

    market_state = eval_result.market_model_results[market_model.market_model_id]
    observations = materialize_market_model_observations(
        market_state,
        frame=frame,
        market_view=market_view,
        context=ObservationMaterializationContext(
            market_model_id=market_model.market_model_id,
            instrument=instrument,
            evaluation_timeframe=evaluation_timeframe,
            source_dataset_ref=source_dataset_ref,
            reference_price_policy=outcome_definition.reference_price_policy,
        ),
    )
    outcome_occurrences = observations_as_outcome_occurrences(observations)
    outcomes = compute_forward_outcomes_for_horizons(
        outcome_occurrences,
        frame=frame,
        ohlcv=ohlcv,
        horizons=request.horizons,
        definition=outcome_definition,
    )

    definition_fingerprint = outcome_definition_fingerprint(request.horizons, outcome_definition)
    run_id = derive_run_id_v2(
        research_scope=ResearchScope.MARKET_MODEL_ONLY,
        source_dataset_ref=source_dataset_ref,
        market_model_ids=(market_model.market_model_id,),
        signal_model_ids=(),
        horizons=request.horizons,
        evaluation_timeframe=evaluation_timeframe.value,
        requested_range_start=request.requested_range.start,
        requested_range_end=request.requested_range.end,
        framework_version=framework_version,
        outcome_definition_fingerprint=definition_fingerprint,
    )
    manifest = SignalResearchRunManifest(
        run_id=run_id,
        schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        source_dataset_ref=source_dataset_ref,
        evaluation_timeframe=evaluation_timeframe.value,
        signal_model_ids=(),
        horizon_bars_requested=request.horizons,
        reference_price_policy=outcome_definition.reference_price_policy,
        outcome_definition_fingerprint=definition_fingerprint,
        experiment_id=request.experiment_id,
        research_scope=ResearchScope.MARKET_MODEL_ONLY,
        market_model_ids=(market_model.market_model_id,),
    )
    return _persist_run(
        request,
        repository=repository,
        manifest=manifest,
        occurrences=empty_signal_occurrences_dataframe(),
        observations=observations,
        context=empty_context_facts_dataframe(),
        outcomes=outcomes,
    )


def _persist_run(
    request: RunSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None,
    manifest: SignalResearchRunManifest,
    occurrences: pl.DataFrame,
    observations: pl.DataFrame,
    context: pl.DataFrame,
    outcomes: pl.DataFrame,
) -> RunSignalResearchResult:
    envelope = SignalResearchRunEnvelope(
        manifest=manifest,
        occurrences=occurrences,
        observations=observations,
        outcomes=outcomes,
        context=context,
    )
    run_ref = RunDatasetRef(run_id=manifest.run_id)
    if request.persist:
        repo = repository or SignalResearchDatasetRepository(request.storage_root)
        run_ref = repo.write(envelope)

    return RunSignalResearchResult(
        run_id=manifest.run_id,
        run_ref=run_ref,
        manifest=manifest,
        occurrences=occurrences,
        observations=observations,
        context=context,
        outcomes=outcomes,
    )
