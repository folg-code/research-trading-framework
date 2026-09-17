"""Session Overlap Window Market Analysis component."""

import numpy as np

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.errors import ComponentValidationError
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import OutputFieldSpec, OutputId, OutputSchema
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("session.overlap_window")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.overlap_window")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_KNOWN_SESSIONS = ("asia", "london", "new_york")
_OVERLAP = OutputId("overlap")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("session_a", ParameterType.STR),
        ParameterFieldSpec("session_b", ParameterType.STR),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_OVERLAP, "float64"),))


def _validate_session_names(session_a: str, session_b: str) -> None:
    for name in (session_a, session_b):
        if name not in _KNOWN_SESSIONS:
            msg = f"unknown session {name!r}; must be one of {_KNOWN_SESSIONS}"
            raise ComponentValidationError(_COMPONENT_ID, msg)
    if session_a == session_b:
        msg = f"session_a and session_b must name two different sessions, both got {session_a!r}"
        raise ComponentValidationError(_COMPONENT_ID, msg)


class OverlapWindowComponent:
    """Causal flag for the window where two named sessions' hours overlap.

    ``overlap = 1.0`` when the bar is simultaneously in both ``session_a``
    and ``session_b`` (each one of ``"asia"``, ``"london"``, ``"new_york"``,
    per ``GlobalSessionCalendarResolver``, ADR-MA-015), else ``0.0``. Always
    defined -- no warmup, no ``NaN`` -- since it is a pure per-bar function
    of session membership. Formerly known in some source material as a
    "killzone"; parametrized by the pair of sessions rather than a fixed
    label.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyOverlapWindowImplementation:
    """NumPy Overlap Window backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        session_a = str(parameters.get("session_a"))
        session_b = str(parameters.get("session_b"))
        _validate_session_names(session_a, session_b)

        metadata = workspace.session_metadata
        if metadata is None:
            raise ComponentValidationError(
                _COMPONENT_ID,
                "session metadata is required; pass a session_resolver to run_analysis",
            )
        bar_count = len(workspace.market)
        if len(metadata) != bar_count:
            raise ComponentValidationError(
                _COMPONENT_ID,
                "session metadata length must match the computation-grid timestamps",
            )

        try:
            in_a = np.asarray(metadata.named_session(session_a), dtype=bool)
            in_b = np.asarray(metadata.named_session(session_b), dtype=bool)
        except ValidationError as exc:
            raise ComponentValidationError(_COMPONENT_ID, str(exc)) from exc
        overlap = (in_a & in_b).astype(np.float64)

        outputs: dict[OutputId, OutputSeries] = {
            _OVERLAP: ndarray_to_output_series(overlap),
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


__all__ = ["NumpyOverlapWindowImplementation", "OverlapWindowComponent"]
