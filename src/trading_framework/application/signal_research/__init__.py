"""Application orchestration for Signal Research runs."""

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchError,
    AnalyzeSignalResearchRequest,
    AnalyzeSignalResearchResult,
    analyze_signal_research_run,
)
from trading_framework.application.signal_research.map_definition import (
    DefinitionMappingError,
    ResolvedSignalResearchDefinition,
    map_definition_to_analyze_request,
    map_definition_to_run_request,
    resolve_signal_research_definition,
)
from trading_framework.application.signal_research.run_signal_research import (
    RunSignalResearchRequest,
    RunSignalResearchResult,
    SignalResearchError,
    run_signal_research,
)
from trading_framework.research.analytics.quality_flags import SignalResearchQualityWarning

__all__ = [
    "AnalyzeSignalResearchError",
    "AnalyzeSignalResearchRequest",
    "AnalyzeSignalResearchResult",
    "DefinitionMappingError",
    "ResolvedSignalResearchDefinition",
    "RunSignalResearchRequest",
    "RunSignalResearchResult",
    "SignalResearchError",
    "SignalResearchQualityWarning",
    "analyze_signal_research_run",
    "map_definition_to_analyze_request",
    "map_definition_to_run_request",
    "resolve_signal_research_definition",
    "run_signal_research",
]
