"""Signal Research dataset persistence."""

from trading_framework.research.datasets.signal_research import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    derive_run_id,
    outcome_definition_fingerprint,
    validate_occurrences_dataframe,
    validate_outcomes_dataframe,
)

__all__ = [
    "SIGNAL_RESEARCH_SCHEMA_VERSION",
    "RunDatasetRef",
    "SignalResearchDatasetRepository",
    "SignalResearchRunEnvelope",
    "SignalResearchRunManifest",
    "derive_run_id",
    "outcome_definition_fingerprint",
    "validate_occurrences_dataframe",
    "validate_outcomes_dataframe",
]
