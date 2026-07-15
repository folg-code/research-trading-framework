"""Map SignalResearchDefinitionSpec to run and analyze orchestration requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchRequest,
)
from trading_framework.application.signal_research.run_signal_research import (
    RunSignalResearchRequest,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.dimensions import GroupDimension
from trading_framework.research.datasets.signal_research import RunDatasetRef
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition
from trading_framework.research.requests import (
    SignalResearchRequest,
    validate_signal_research_request,
)
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import (
    ResearchGroupingDimension,
    SignalResearchDefinitionSpec,
)
from trading_framework.research.signal_research.horizons import horizons_to_bars
from trading_framework.research.signal_research.model_registry import (
    ResolvedModels,
    resolve_models_from_definition,
)
from trading_framework.time.sessions.protocol import TradingSessionResolver


class DefinitionMappingError(ValidationError):
    """Raised when a definition cannot be mapped to orchestration requests."""


@dataclass(frozen=True, slots=True)
class ResolvedSignalResearchDefinition:
    """Fully resolved definition ready for orchestration."""

    spec: SignalResearchDefinitionSpec
    models: ResolvedModels
    horizon_bars: tuple[int, ...]


def resolve_signal_research_definition(
    spec: SignalResearchDefinitionSpec,
) -> ResolvedSignalResearchDefinition:
    """Resolve model aliases and attach lineage metadata to the definition."""
    models = resolve_models_from_definition(spec)
    resolved_spec = spec.with_resolution(
        resolved_parameters=models.resolved_parameters,
        component_lineage_hashes=models.component_lineage_hashes,
    )
    horizon_bars = horizons_to_bars(
        resolved_spec.horizons,
        evaluation_timeframe=resolved_spec.evaluation_timeframe,
    )
    return ResolvedSignalResearchDefinition(
        spec=resolved_spec,
        models=models,
        horizon_bars=horizon_bars,
    )


def map_definition_to_run_request(
    resolved: ResolvedSignalResearchDefinition,
    *,
    storage_root: Path,
    session_resolver: TradingSessionResolver | None = None,
    persist: bool = True,
) -> RunSignalResearchRequest:
    """Map a resolved definition to ``RunSignalResearchRequest``."""
    spec = resolved.spec
    outcome_definition = ForwardOutcomeDefinition(horizon_bars=resolved.horizon_bars[0])
    validate_signal_research_request(
        SignalResearchRequest(
            scope=spec.research_scope,
            dataset_ref=spec.dataset_ref,
            market_models=resolved.models.market_models,
            signal_models=resolved.models.signal_models,
            outcome_definition=outcome_definition,
        )
    )

    return RunSignalResearchRequest(
        dataset_ref=spec.dataset_ref,
        timeframe=spec.evaluation_timeframe,
        requested_range=spec.time_range,
        storage_root=storage_root,
        signal_models=resolved.models.signal_models,
        horizons=resolved.horizon_bars,
        scope=spec.research_scope,
        market_models=resolved.models.market_models,
        evaluation_timeframe=spec.evaluation_timeframe,
        session_resolver=session_resolver,
        outcome_definition=outcome_definition,
        experiment_id=spec.research_id,
        persist=persist,
        research_id=spec.research_id,
        research_question=spec.research_question,
        definition_hash=spec.definition_hash,
        occurrence_policy=spec.occurrence_policy.to_dict(),
    )


def map_definition_to_analyze_request(
    resolved: ResolvedSignalResearchDefinition,
    *,
    run_ref: RunDatasetRef,
    storage_root: Path,
) -> AnalyzeSignalResearchRequest:
    """Map a resolved definition to ``AnalyzeSignalResearchRequest``."""
    spec = resolved.spec
    return AnalyzeSignalResearchRequest(
        run_ref=run_ref,
        storage_root=storage_root,
        horizons=resolved.horizon_bars,
        group_by=_map_grouping_dimensions(spec.grouping),
        conditional_context=spec.research_scope is ResearchScope.MARKET_AND_SIGNAL,
        interpretation_min_sample_size=spec.quality_rules.minimum_sample_size,
        quality_rules=spec.quality_rules,
    )


def _map_grouping_dimensions(
    grouping: tuple[ResearchGroupingDimension, ...],
) -> tuple[GroupDimension, ...]:
    mapped: list[GroupDimension] = []
    for dimension in grouping:
        if dimension is ResearchGroupingDimension.MONTH:
            mapped.append(GroupDimension.CALENDAR_MONTH)
            continue
        if dimension is ResearchGroupingDimension.SESSION:
            mapped.append(GroupDimension.RTH_MEMBERSHIP)
            continue
        if dimension is ResearchGroupingDimension.TIME_OF_DAY:
            mapped.append(GroupDimension.TIME_OF_DAY)
            continue
        assert_never(dimension)
    return tuple(mapped)
