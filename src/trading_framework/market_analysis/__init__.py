"""Market Analysis domain package."""

from trading_framework.market_analysis.data import AnalysisDataView, DataColumn
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
from trading_framework.market_analysis.planning import (
    CyclicDependencyError,
    DependencyPlanner,
    ExecutionPlan,
    PlannedNode,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.protocols import (
    BatchAnalysisComponent,
    ComponentImplementation,
)
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage import (
    AnalysisResultStore,
    AnalysisWorkspace,
    AnalysisWorkspaceView,
)

__all__ = [
    "AnalysisContext",
    "AnalysisDataView",
    "AnalysisResult",
    "AnalysisResultStore",
    "AnalysisWorkspace",
    "AnalysisWorkspaceView",
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
    "ComponentRegistry",
    "ComponentRequest",
    "ComponentVersion",
    "ComputationIdentity",
    "CyclicDependencyError",
    "DataColumn",
    "DataFieldDependency",
    "DependencyPlanner",
    "ExecutionPlan",
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
    "PlannedNode",
    "PlanningContext",
    "PlanningRequest",
    "TimeRange",
    "ValidityMetadata",
    "WarmUpMetadata",
]
