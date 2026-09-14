"""Signal Research methodology contracts — definition spec and loaders."""

from trading_framework.research.signal_research.definition import (
    SIGNAL_RESEARCH_DEFINITION_SCHEMA_V1,
    SUPPORTED_SIGNAL_RESEARCH_DEFINITION_SCHEMA_VERSIONS,
    BaselineType,
    CandidateBounds,
    OccurrencePolicy,
    OccurrencePolicyType,
    ResearchGroupingDimension,
    SignalResearchDefinitionSpec,
    SignalResearchQualityRules,
    UnsupportedSignalResearchDefinitionSchemaError,
    compute_definition_hash,
    validate_signal_research_definition,
)
from trading_framework.research.signal_research.loader import (
    load_signal_research_definition,
    load_signal_research_definition_from_dict,
)
from trading_framework.research.signal_research.model_registry import (
    ResolvedModels,
    is_known_market_model_alias,
    is_known_signal_model_alias,
    resolve_models_from_definition,
)
from trading_framework.research.signal_research.template_catalog import (
    SignalResearchTemplateSummary,
    TemplateApplicationError,
    TemplateSource,
    TemplateStatus,
    apply_signal_research_template,
    list_signal_research_templates,
)

__all__ = [
    "SIGNAL_RESEARCH_DEFINITION_SCHEMA_V1",
    "SUPPORTED_SIGNAL_RESEARCH_DEFINITION_SCHEMA_VERSIONS",
    "BaselineType",
    "CandidateBounds",
    "OccurrencePolicy",
    "OccurrencePolicyType",
    "ResearchGroupingDimension",
    "ResolvedModels",
    "SignalResearchDefinitionSpec",
    "SignalResearchQualityRules",
    "SignalResearchTemplateSummary",
    "TemplateApplicationError",
    "TemplateSource",
    "TemplateStatus",
    "UnsupportedSignalResearchDefinitionSchemaError",
    "apply_signal_research_template",
    "compute_definition_hash",
    "is_known_market_model_alias",
    "is_known_signal_model_alias",
    "list_signal_research_templates",
    "load_signal_research_definition",
    "load_signal_research_definition_from_dict",
    "resolve_models_from_definition",
    "validate_signal_research_definition",
]
