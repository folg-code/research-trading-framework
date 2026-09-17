"""Session Current Period Extreme Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.period_extreme import (
    period_keys,
    running_and_previous_period_extreme,
)
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

_COMPONENT_ID = ComponentId("session.current_period_extreme")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.current_period_extreme")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_KNOWN_PERIODS = ("day", "week")
_KNOWN_SIDES = ("high", "low")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.STR),
        ParameterFieldSpec("side", ParameterType.STR),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


def _validate(period: str, side: str) -> None:
    if period not in _KNOWN_PERIODS:
        msg = f"unknown period {period!r}; must be one of {_KNOWN_PERIODS}"
        raise ComponentValidationError(_COMPONENT_ID, msg)
    if side not in _KNOWN_SIDES:
        msg = f"unknown side {side!r}; must be one of {_KNOWN_SIDES}"
        raise ComponentValidationError(_COMPONENT_ID, msg)


class CurrentPeriodExtremeComponent:
    """Causal running high/low of the current day or week period, so far.

    ``value`` is the running maximum (``side="high"``) or minimum
    (``side="low"``) of the bar's own ``side`` column within the current
    ``period`` ("day" or "week", grouped from ``session_metadata.trading_days``
    -- any resolver works, no named-session column required). Always
    causal: a bar's value reflects only that period's bars up to and
    including itself, never the period's eventual final extreme.
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
        side = str(parameters.get("side"))
        return (DataFieldDependency(side),) if side in _KNOWN_SIDES else ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyCurrentPeriodExtremeImplementation:
    """NumPy Current Period Extreme backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = str(parameters.get("period"))
        side = str(parameters.get("side"))
        _validate(period, side)

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

        column = workspace.market.high if side == "high" else workspace.market.low
        values = np.asarray(column.values, dtype=np.float64)
        keys = period_keys(metadata.trading_days, period=period)
        arrays = running_and_previous_period_extreme(values, keys=keys, side=side)

        outputs: dict[OutputId, OutputSeries] = {
            _VALUE: ndarray_to_output_series(arrays.current),
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


__all__ = ["CurrentPeriodExtremeComponent", "NumpyCurrentPeriodExtremeImplementation"]
