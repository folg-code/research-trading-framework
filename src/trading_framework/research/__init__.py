"""Research domain package."""

from trading_framework.research.context import (
    align_context_facts_at_available_at,
    empty_context_facts_dataframe,
    validate_context_facts_dataframe,
)
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    derive_run_id,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations import (
    MarketModelObservationPolicy,
    ObservationMaterializationContext,
    derive_observation_id,
    empty_market_model_observations_dataframe,
    materialize_market_model_observations,
    validate_observations_dataframe,
)
from trading_framework.research.outcomes import (
    ForwardOutcomeDefinition,
    IncompleteHorizonPolicy,
    OutcomeStatus,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes,
    compute_forward_outcomes_for_horizons,
    empty_forward_outcomes_dataframe,
)
from trading_framework.research.requests import (
    SignalResearchRequest,
    SignalResearchRequestError,
    validate_signal_research_request,
)
from trading_framework.research.scope import ResearchScope

__all__ = [
    "SIGNAL_RESEARCH_SCHEMA_VERSION",
    "ForwardOutcomeDefinition",
    "IncompleteHorizonPolicy",
    "MarketModelObservationPolicy",
    "ObservationMaterializationContext",
    "OutcomeStatus",
    "ResearchScope",
    "RunDatasetRef",
    "SignalResearchDatasetRepository",
    "SignalResearchRequest",
    "SignalResearchRequestError",
    "SignalResearchRunEnvelope",
    "SignalResearchRunManifest",
    "align_context_facts_at_available_at",
    "align_ohlcv_to_evaluation_frame",
    "compute_forward_outcomes",
    "compute_forward_outcomes_for_horizons",
    "derive_observation_id",
    "derive_run_id",
    "empty_context_facts_dataframe",
    "empty_forward_outcomes_dataframe",
    "empty_market_model_observations_dataframe",
    "materialize_market_model_observations",
    "outcome_definition_fingerprint",
    "validate_context_facts_dataframe",
    "validate_observations_dataframe",
    "validate_signal_research_request",
]
