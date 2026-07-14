"""Research dataset persistence."""

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
    validate_occurrences_dataframe,
    validate_outcomes_dataframe,
)
from trading_framework.research.datasets.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    StrategyResearchDatasetRepository,
    StrategyResearchRunEnvelope,
    StrategyResearchRunManifest,
    StrategyResearchRunRef,
    derive_strategy_run_id,
    validate_equity_dataframe,
    validate_trades_dataframe,
)

__all__ = [
    "SIGNAL_RESEARCH_SCHEMA_V2",
    "SIGNAL_RESEARCH_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_SCHEMA_VERSION",
    "RunDatasetRef",
    "SignalResearchDatasetRepository",
    "SignalResearchRunEnvelope",
    "SignalResearchRunManifest",
    "StrategyResearchDatasetRepository",
    "StrategyResearchRunEnvelope",
    "StrategyResearchRunManifest",
    "StrategyResearchRunRef",
    "derive_run_id",
    "derive_run_id_v2",
    "derive_strategy_run_id",
    "outcome_definition_fingerprint",
    "validate_equity_dataframe",
    "validate_occurrences_dataframe",
    "validate_outcomes_dataframe",
    "validate_trades_dataframe",
]
