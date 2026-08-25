"""Session Range Market Analysis component."""

from __future__ import annotations

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.session_range import session_range
from trading_framework.market_analysis.errors import ComponentValidationError
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import (
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterSchema,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("structure.session_range")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.session_range")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SESSION_OPEN = OutputId("session_open")
_SESSION_HIGH = OutputId("session_high")
_SESSION_LOW = OutputId("session_low")
_SESSION_CLOSE = OutputId("session_close")
_SESSION_RANGE = OutputId("session_range")
_SESSION_COMPLETED = OutputId("session_completed")

_PARAMETER_SCHEMA = ParameterSchema(fields=())
_EVENT_ALIGNMENT = AlignmentPolicy.EVENT_AT_AVAILABLE


def _state_output(output_id: OutputId) -> OutputFieldSpec:
    return OutputFieldSpec(output_id, "float64", group=OutputGroup.CORE)


def _completed_event_output() -> OutputFieldSpec:
    return OutputFieldSpec(
        _SESSION_COMPLETED,
        "float64",
        group=OutputGroup.CORE,
        alignment_policy=_EVENT_ALIGNMENT,
        inactive_event_fill=0.0,
    )


_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        _state_output(_SESSION_OPEN),
        _state_output(_SESSION_HIGH),
        _state_output(_SESSION_LOW),
        _state_output(_SESSION_CLOSE),
        _state_output(_SESSION_RANGE),
        _completed_event_output(),
    )
)


class SessionRangeComponent:
    """Causal running ES RTH session open/high/low/close/range.

    Grouping uses ``(trading_day, is_rth)``. Outputs are NaN outside RTH.
    ``session_completed`` is 1.0 only on the last RTH bar of a group that has a
    later bar proving the session ended.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.STRUCTURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("open"),
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpySessionRangeImplementation:
    """NumPy Session Range backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        metadata = workspace.session_metadata
        if metadata is None:
            raise ComponentValidationError(
                _COMPONENT_ID,
                "session metadata is required; pass session_resolver to run_analysis",
            )
        bar_count = len(workspace.market)
        if len(metadata) != bar_count:
            raise ComponentValidationError(
                _COMPONENT_ID,
                "session metadata length must match the computation-grid timestamps",
            )
        arrays = session_range(
            np.asarray(workspace.market.open.values, dtype=np.float64),
            np.asarray(workspace.market.high.values, dtype=np.float64),
            np.asarray(workspace.market.low.values, dtype=np.float64),
            np.asarray(workspace.market.close.values, dtype=np.float64),
            is_rth=np.asarray(metadata.is_rth, dtype=bool),
            trading_day_ordinal=np.array(
                [day.toordinal() for day in metadata.trading_days],
                dtype=np.int32,
            ),
        )
        outputs: dict[OutputId, OutputSeries] = {
            _SESSION_OPEN: ndarray_to_output_series(arrays.session_open),
            _SESSION_HIGH: ndarray_to_output_series(arrays.session_high),
            _SESSION_LOW: ndarray_to_output_series(arrays.session_low),
            _SESSION_CLOSE: ndarray_to_output_series(arrays.session_close),
            _SESSION_RANGE: ndarray_to_output_series(arrays.session_range),
            _SESSION_COMPLETED: OutputSeries(
                values=tuple(float(value) for value in arrays.session_completed),
                dtype="float64",
                inactive_event_fill=0.0,
            ),
        }
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=(),
            output_schema=_OUTPUT_SCHEMA,
            outputs=outputs,
            warmup_bars=0,
            valid_from_index=0,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NumpySessionRangeImplementation", "SessionRangeComponent"]
