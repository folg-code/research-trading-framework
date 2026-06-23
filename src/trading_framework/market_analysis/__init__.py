"""Market Analysis domain package."""

from trading_framework.market_analysis.identity import (
    ComponentId,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.availability import (
    AvailabilityMetadata,
    AvailabilityPolicy,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement, WarmUpMetadata
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.lineage import Lineage
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import (
    ComponentOutputRef,
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.result import (
    AnalysisResult,
    OutputSeries,
    ValidityMetadata,
)
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.protocols import (
    BatchAnalysisComponent,
    ComponentImplementation,
)

__all__ = [
    "AnalysisContext",
    "AnalysisResult",
    "AvailabilityMetadata",
    "AvailabilityPolicy",
    "BatchAnalysisComponent",
    "CanonicalParameters",
    "Causality",
    "ComponentDependency",
    "ComponentId",
    "ComponentImplementation",
    "ComponentKind",
    "ComponentOutputRef",
    "ComponentRequest",
    "ComponentVersion",
    "ComputationIdentity",
    "DataFieldDependency",
    "HistoryRequirement",
    "ImplementationId",
    "ImplementationVersion",
    "Lineage",
    "OutputFieldSpec",
    "OutputGroup",
    "OutputId",
    "OutputRef",
    "OutputSchema",
    "OutputSeries",
    "ParameterFieldSpec",
    "ParameterSchema",
    "ParameterType",
    "TimeRange",
    "ValidityMetadata",
    "WarmUpMetadata",
]
