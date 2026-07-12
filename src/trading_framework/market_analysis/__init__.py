"""Market Analysis domain package."""

from trading_framework.market_analysis.assembly import (
    AnalysisFrame,
    AnalysisFrameAssembler,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.data import AnalysisDataView, DataColumn
from trading_framework.market_analysis.errors import (
    CacheError,
    ComponentValidationError,
    CyclicDependencyError,
    ImplementationExecutionError,
    MarketAnalysisError,
    OutputValidationError,
    PlanningError,
)
from trading_framework.market_analysis.execution import (
    ExecutionCache,
    SequentialBatchExecutor,
    validate_analysis_result,
)
from trading_framework.market_analysis.execution.warmup import (
    extend_computation_range,
    max_history_requirement,
)
from trading_framework.market_analysis.identity import (
    AlignmentIdentity,
    ComponentId,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    ResampleIdentity,
)
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
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
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.market_analysis.models.result import (
    AnalysisResult,
    OutputSeries,
    ValidityMetadata,
)
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    ExecutionPlan,
    PlannedNode,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
    ResolvedComponentRequest,
    RunTimeframeContext,
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
    "AlignmentIdentity",
    "AlignmentPolicy",
    "AnalysisContext",
    "AnalysisDataView",
    "AnalysisFrame",
    "AnalysisFrameAssembler",
    "AnalysisFrameColumnSpec",
    "AnalysisFrameRequest",
    "AnalysisResult",
    "AnalysisResultStore",
    "AnalysisWorkspace",
    "AnalysisWorkspaceView",
    "AvailabilityMetadata",
    "AvailabilityPolicy",
    "BatchAnalysisComponent",
    "CacheError",
    "CanonicalParameters",
    "Causality",
    "ComponentDependency",
    "ComponentId",
    "ComponentImplementation",
    "ComponentKind",
    "ComponentOutputRef",
    "ComponentRegistry",
    "ComponentRequest",
    "ComponentValidationError",
    "ComponentVersion",
    "ComputationIdentity",
    "CyclicDependencyError",
    "DataColumn",
    "DataFieldDependency",
    "DependencyPlanner",
    "ExecutionCache",
    "ExecutionPlan",
    "HistoryRequirement",
    "ImplementationExecutionError",
    "ImplementationId",
    "ImplementationVersion",
    "Lineage",
    "MarketAnalysisError",
    "OutputFieldSpec",
    "OutputGroup",
    "OutputId",
    "OutputRef",
    "OutputSchema",
    "OutputSeries",
    "OutputValidationError",
    "ParameterFieldSpec",
    "ParameterSchema",
    "ParameterType",
    "PlannedNode",
    "PlanningContext",
    "PlanningError",
    "PlanningRequest",
    "RequestResolver",
    "ResampleIdentity",
    "ResampleSpec",
    "ResolvedComponentRequest",
    "RunTimeframeContext",
    "SequentialBatchExecutor",
    "TimeRange",
    "ValidityMetadata",
    "WarmUpMetadata",
    "extend_computation_range",
    "max_history_requirement",
    "validate_analysis_result",
]
