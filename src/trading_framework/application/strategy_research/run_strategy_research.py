"""Run Strategy Research — model evaluation, simulation, persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    resolve_analysis_computation_range,
)
from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical_columnar,
)
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.application.strategy_research.entry_signals import build_gated_entry_signals
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.profiling import optional_phase
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.research.datasets.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    StrategyResearchDatasetRepository,
    StrategyResearchRunEnvelope,
    StrategyResearchRunManifest,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.simulation import (
    BarSequentialSimulator,
    SimulationAssumptions,
    simulation_assumptions_fingerprint,
)
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
from trading_framework.strategy.strategy_model import (
    StrategyModelDefinition,
    validate_strategy_model_definition,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class StrategyResearchError(ValidationError):
    """Raised when Strategy Research orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunStrategyResearchRequest:
    """Input for one Strategy Research run."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    strategy_model: StrategyModelDefinition
    assumptions: SimulationAssumptions
    evaluation_timeframe: Timeframe | None = None
    session_resolver: TradingSessionResolver | None = None
    experiment_id: str | None = None
    persist: bool = True


@dataclass(frozen=True, slots=True)
class RunStrategyResearchResult:
    """Outcome of one Strategy Research run."""

    run_id: str
    run_ref: StrategyResearchRunRef
    manifest: StrategyResearchRunManifest
    trades: pl.DataFrame
    equity: pl.DataFrame


def run_strategy_research(
    request: RunStrategyResearchRequest,
    *,
    repository: StrategyResearchDatasetRepository | None = None,
) -> RunStrategyResearchResult:
    """Evaluate strategy models, simulate trades, and optionally persist the run."""
    validate_strategy_model_definition(request.strategy_model)
    strategy_model = request.strategy_model
    exit_model = _require_fixed_bars_exit(strategy_model)
    risk_model = _require_fixed_quantity_risk(strategy_model)

    evaluation_timeframe = request.evaluation_timeframe or request.timeframe
    dependencies = collect_model_dependencies(
        market_models=(strategy_model.market_model,),
        signal_models=(strategy_model.signal_model,),
    )
    frame_request = build_analysis_frame_request(dependencies)
    analysis_request = RunAnalysisRequest(
        dataset_ref=request.dataset_ref,
        timeframe=request.timeframe,
        requested_range=request.requested_range,
        storage_root=request.storage_root,
        component_requests=dependencies.component_requests,
        frame_request=frame_request,
        evaluation_timeframe=evaluation_timeframe,
        session_resolver=request.session_resolver,
    )
    with optional_phase("strategy_research.plan_computation_range"):
        computation_range = resolve_analysis_computation_range(analysis_request)
    with optional_phase("strategy_research.load_ohlcv"):
        preloaded_column_batch = query_historical_columnar(
            QueryHistoricalRequest(
                dataset_ref=request.dataset_ref,
                start_at=computation_range.start,
                end_at=computation_range.end,
            ),
            storage_root=request.storage_root,
        )
        preloaded_view = preloaded_column_batch.to_analysis_view()
    with optional_phase("strategy_research.evaluate_models"):
        eval_result = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=request.dataset_ref,
                timeframe=request.timeframe,
                requested_range=request.requested_range,
                storage_root=request.storage_root,
                market_models=(strategy_model.market_model,),
                signal_models=(strategy_model.signal_model,),
                evaluation_timeframe=evaluation_timeframe,
                session_resolver=request.session_resolver,
                preloaded_column_batch=preloaded_column_batch,
                preloaded_view=preloaded_view,
            )
        )
    frame = eval_result.analysis.frame
    if frame is None:
        msg = "strategy research requires an assembled AnalysisFrame"
        raise StrategyResearchError(msg)

    with optional_phase("strategy_research.build_entry_signals"):
        signal_emissions = eval_result.signal_model_emissions[
            strategy_model.signal_model.signal_model_id
        ]
        market_state = eval_result.market_model_results[strategy_model.market_model.market_model_id]
        entry_signals = build_gated_entry_signals(
            signal_emissions=signal_emissions,
            market_state=market_state,
        )
        simulation_column_batch = preloaded_column_batch.slice_observed_range(
            request.requested_range
        )

    source_dataset_ref = str(request.dataset_ref)
    instrument = request.dataset_ref.dataset_id.instrument_id.value
    with optional_phase("strategy_research.simulate"):
        simulation = BarSequentialSimulator().simulate_from_columnar(
            column_batch=simulation_column_batch,
            entry_signals=entry_signals,
            strategy_model=strategy_model,
            assumptions=request.assumptions,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
        )

    assumptions_fingerprint = simulation_assumptions_fingerprint(request.assumptions)
    run_id = derive_strategy_run_id(
        strategy_model_id=strategy_model.strategy_model_id,
        market_model_id=strategy_model.market_model.market_model_id,
        signal_model_id=strategy_model.signal_model.signal_model_id,
        exit_model_id=exit_model.exit_model_id,
        exit_after_bars=exit_model.exit_after_bars,
        risk_model_id=risk_model.risk_model_id,
        position_quantity=format(risk_model.position_quantity(), "f"),
        source_dataset_ref=source_dataset_ref,
        evaluation_timeframe=evaluation_timeframe.value,
        requested_range_start=request.requested_range.start,
        requested_range_end=request.requested_range.end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
    )
    manifest = StrategyResearchRunManifest(
        run_id=run_id,
        schema_version=STRATEGY_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime.now(tz=UTC),
        source_dataset_ref=source_dataset_ref,
        evaluation_timeframe=evaluation_timeframe.value,
        strategy_model_id=strategy_model.strategy_model_id,
        market_model_id=strategy_model.market_model.market_model_id,
        signal_model_id=strategy_model.signal_model.signal_model_id,
        exit_model_id=exit_model.exit_model_id,
        risk_model_id=risk_model.risk_model_id,
        simulation_assumptions_fingerprint=assumptions_fingerprint,
        experiment_id=request.experiment_id,
    )
    envelope = StrategyResearchRunEnvelope(
        manifest=manifest,
        trades=simulation.trades,
        equity=simulation.equity,
    )
    run_ref = StrategyResearchRunRef(run_id=run_id)
    if request.persist:
        with optional_phase("strategy_research.persist_run"):
            repo = repository or StrategyResearchDatasetRepository(request.storage_root)
            run_ref = repo.write(envelope)

    return RunStrategyResearchResult(
        run_id=run_id,
        run_ref=run_ref,
        manifest=manifest,
        trades=simulation.trades,
        equity=simulation.equity,
    )


def _require_fixed_bars_exit(strategy_model: StrategyModelDefinition) -> FixedBarsExitModel:
    exit_model = strategy_model.exit_model
    if not isinstance(exit_model, FixedBarsExitModel):
        msg = "run_strategy_research supports FixedBarsExitModel only"
        raise StrategyResearchError(msg)
    return exit_model


def _require_fixed_quantity_risk(strategy_model: StrategyModelDefinition) -> FixedQuantityRiskModel:
    risk_model = strategy_model.risk_model
    if not isinstance(risk_model, FixedQuantityRiskModel):
        msg = "run_strategy_research supports FixedQuantityRiskModel only"
        raise StrategyResearchError(msg)
    return risk_model
