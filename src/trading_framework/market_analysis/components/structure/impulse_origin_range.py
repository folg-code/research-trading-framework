"""Structure Impulse Origin Range Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.impulse import impulse_directions
from trading_framework.market_analysis.adapters.numpy.impulse_origin_range import (
    impulse_origin_range,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    dependency_results_values,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.volatility.atr import AtrComponent
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
from trading_framework.market_analysis.models.outputs import (
    ComponentOutputRef,
    OutputFieldSpec,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("structure.impulse_origin_range")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.impulse_origin_range")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")

_ORIGIN_EVENT = OutputId("origin_event")
_ORIGIN_HIGH = OutputId("origin_high")
_ORIGIN_LOW = OutputId("origin_low")
_ROLE_ACTIVE = OutputId("role_active")

_WARMUP_BARS = 1

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("impulse_atr_multiple", ParameterType.FLOAT, default=1.5, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_ORIGIN_EVENT, "float64"),
        OutputFieldSpec(_ORIGIN_HIGH, "float64"),
        OutputFieldSpec(_ORIGIN_LOW, "float64"),
        OutputFieldSpec(_ROLE_ACTIVE, "float64"),
    )
)


class ImpulseOriginRangeComponent:
    """Causal last opposite-direction bar preceding a directional impulse ("order block").

    A bar is impulsive when its body ``|close - open|`` spans at least
    ``impulse_atr_multiple`` times the concurrent ATR. When bar ``i`` is
    impulsive and bar ``i-1``'s own body is the opposite direction, bar
    ``i-1`` becomes the active "origin range": ``origin_event = 1.0`` at
    bar ``i`` (the confirming bar), and ``origin_high``/``origin_low``
    (bar ``i-1``'s own high/low) plus ``role_active`` (``1.0``) are
    forward-filled from ``i`` onward.

    ``role_active`` flips to ``0.0`` (invalidated) once a later bar's close
    breaks back through the range -- below ``origin_low`` for a bullish
    impulse's (bearish) origin, above ``origin_high`` for a bearish
    impulse's (bullish) origin -- carrying the "breaker" case as a field on
    this component rather than a separate one, per the naming convention.
    A new origin_event always replaces whatever range was previously
    active, invalidated or not.

    Depends on ``volatility.atr`` keyed by ``period``. Warm-up:
    ``max(1, period - 1)`` bars. Default ``impulse_atr_multiple = 1.5``
    (D-P19-05): a starting, calibratable threshold, not a fixed constant.
    A zero ATR (perfectly flat recent bars) collapses the threshold to
    zero, so any non-flat bar would trivially qualify as impulsive -- an
    extreme, unlikely-in-real-data degenerate case, not special-cased,
    same spirit as this catalog's other zero-denominator conventions.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=_WARMUP_BARS)

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
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": period}),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyImpulseOriginRangeImplementation:
    """NumPy Impulse Origin Range backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        impulse_atr_multiple = float(parameters.get("impulse_atr_multiple"))
        bar_count = len(workspace.market)
        open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )
        direction = impulse_directions(
            open_, close, atr_values, impulse_atr_multiple=impulse_atr_multiple
        )
        arrays = impulse_origin_range(open_, high, low, close, direction)

        outputs: dict[OutputId, OutputSeries] = {
            _ORIGIN_EVENT: ndarray_to_output_series(arrays.origin_event),
            _ORIGIN_HIGH: ndarray_to_output_series(arrays.origin_high),
            _ORIGIN_LOW: ndarray_to_output_series(arrays.origin_low),
            _ROLE_ACTIVE: ndarray_to_output_series(arrays.role_active),
        }
        warmup_bars = max(_WARMUP_BARS, period - 1)
        dependency_keys = tuple(sorted(workspace.dependency_results))
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=dependency_keys,
            output_schema=_OUTPUT_SCHEMA,
            outputs=outputs,
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["ImpulseOriginRangeComponent", "NumpyImpulseOriginRangeImplementation"]
