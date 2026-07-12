"""Research domain package."""

from trading_framework.research.datasets import (
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
    IncompleteHorizonPolicy,
    OutcomeStatus,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes,
    compute_forward_outcomes_for_horizons,
    empty_forward_outcomes_dataframe,
)

__all__ = [
    "SIGNAL_RESEARCH_SCHEMA_VERSION",
    "ForwardOutcomeDefinition",
    "IncompleteHorizonPolicy",
    "OutcomeStatus",
    "RunDatasetRef",
    "SignalResearchDatasetRepository",
    "SignalResearchRunEnvelope",
    "SignalResearchRunManifest",
    "align_ohlcv_to_evaluation_frame",
    "compute_forward_outcomes",
    "compute_forward_outcomes_for_horizons",
    "derive_run_id",
    "empty_forward_outcomes_dataframe",
    "outcome_definition_fingerprint",
]
