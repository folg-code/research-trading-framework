"""Application orchestration for Signal Research runs."""

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchError,
    AnalyzeSignalResearchRequest,
    AnalyzeSignalResearchResult,
    analyze_signal_research_run,
)
from trading_framework.application.signal_research.list_known_models import (
    KnownModelAliases,
    list_known_model_aliases,
)
from trading_framework.application.signal_research.list_signal_research_templates import (
    ApplySignalResearchTemplateRequest,
    SignalResearchTemplateNotFoundError,
    SignalResearchTemplateSummary,
    TemplateSource,
    TemplateStatus,
    apply_signal_research_template,
    list_signal_research_templates,
)
from trading_framework.application.signal_research.map_definition import (
    DefinitionMappingError,
    ResolvedSignalResearchDefinition,
    map_definition_to_analyze_request,
    map_definition_to_run_request,
    resolve_signal_research_definition,
)
from trading_framework.application.signal_research.persist_analytics import (
    PersistSignalResearchAnalyticsError,
    PersistSignalResearchAnalyticsResult,
    load_signal_research_analytics,
    persist_signal_research_analytics,
)
from trading_framework.application.signal_research.render_signal_research_report import (
    RenderSignalResearchReportError,
    RenderSignalResearchReportRequest,
    RenderSignalResearchReportResult,
    render_signal_research_report,
)
from trading_framework.application.signal_research.run_signal_research import (
    RunSignalResearchRequest,
    RunSignalResearchResult,
    SignalResearchError,
    run_signal_research,
)
from trading_framework.application.signal_research.run_signal_research_family import (
    FamilyVariantResult,
    RunSignalResearchFamilyError,
    RunSignalResearchFamilyRequest,
    RunSignalResearchFamilyResult,
    run_signal_research_family_experiment,
)
from trading_framework.research.analytics.quality_flags import SignalResearchQualityWarning

__all__ = [
    "AnalyzeSignalResearchError",
    "AnalyzeSignalResearchRequest",
    "AnalyzeSignalResearchResult",
    "ApplySignalResearchTemplateRequest",
    "DefinitionMappingError",
    "FamilyVariantResult",
    "KnownModelAliases",
    "PersistSignalResearchAnalyticsError",
    "PersistSignalResearchAnalyticsResult",
    "RenderSignalResearchReportError",
    "RenderSignalResearchReportRequest",
    "RenderSignalResearchReportResult",
    "ResolvedSignalResearchDefinition",
    "RunSignalResearchFamilyError",
    "RunSignalResearchFamilyRequest",
    "RunSignalResearchFamilyResult",
    "RunSignalResearchRequest",
    "RunSignalResearchResult",
    "SignalResearchError",
    "SignalResearchQualityWarning",
    "SignalResearchTemplateNotFoundError",
    "SignalResearchTemplateSummary",
    "TemplateSource",
    "TemplateStatus",
    "analyze_signal_research_run",
    "apply_signal_research_template",
    "list_known_model_aliases",
    "list_signal_research_templates",
    "load_signal_research_analytics",
    "map_definition_to_analyze_request",
    "map_definition_to_run_request",
    "persist_signal_research_analytics",
    "render_signal_research_report",
    "resolve_signal_research_definition",
    "run_signal_research",
    "run_signal_research_family_experiment",
]
