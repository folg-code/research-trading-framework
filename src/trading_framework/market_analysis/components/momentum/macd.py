"""MACD momentum feature component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import ema
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.trend.ema import EmaComponent
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

_COMPONENT_ID = ComponentId("momentum.macd")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.macd")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_EMA_ID = ComponentId("trend.ema")
_EMA_VALUE_OUTPUT = OutputId("value")

_LINE_OUTPUT = OutputId("line")
_SIGNAL_OUTPUT = OutputId("signal")
_HISTOGRAM_OUTPUT = OutputId("histogram")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("fast_period", ParameterType.INT, default=12, minimum=1),
        ParameterFieldSpec("slow_period", ParameterType.INT, default=26, minimum=1),
        ParameterFieldSpec("signal_period", ParameterType.INT, default=9, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_LINE_OUTPUT, "float64"),
        OutputFieldSpec(_SIGNAL_OUTPUT, "float64"),
        OutputFieldSpec(_HISTOGRAM_OUTPUT, "float64"),
    )
)


def _validate_periods(fast_period: int, slow_period: int) -> None:
    if fast_period >= slow_period:
        raise ComponentValidationError(
            _COMPONENT_ID,
            f"fast_period ({fast_period}) must be less than slow_period ({slow_period})",
        )


def _ema_result_for_period(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    period: int,
) -> AnalysisResult:
    for result in dependency_results.values():
        identity = result.computation_identity
        if identity.component_id == _EMA_ID and identity.parameters.get("period") == period:
            return result
    raise ComponentValidationError(
        _COMPONENT_ID,
        f"missing trend.ema dependency result for period={period}",
    )


class MacdComponent:
    """Semantic MACD feature: fast/slow EMA difference plus signal and histogram.

    Depends on two ``trend.ema`` outputs (Finding 4, SPRINT_051.md) rather than
    re-deriving the EMA kernel -- the direct structural sibling of
    ``volatility.range_expansion`` and ``trend.ema_distance`` (components that
    depend on other components rather than raw market data).

    ``line = ema(fast_period) - ema(slow_period)``
    ``signal = ema(line, signal_period)`` -- the shared ``ema`` kernel applied
    directly to the ``line`` series computed inside this component, because
    ``trend.ema`` reads ``close`` from the workspace and cannot smooth another
    component's output (D-S051-05).
    ``histogram = line - signal``

    Warmup is derived from the dependency results themselves rather than
    recomputed independently from the parameters: ``line`` becomes valid once
    both EMAs are (``max`` of their ``valid_from_index`` -- the slow EMA's,
    since ``fast_period < slow_period`` is enforced), and ``signal`` needs a
    further ``signal_period - 1`` valid ``line`` bars before it, matching the
    ``ema`` kernel's own SMA-seeded warmup convention exactly.
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
        fast_period = int(parameters.get("fast_period"))
        slow_period = int(parameters.get("slow_period"))
        _validate_periods(fast_period, slow_period)
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_EMA_ID,
                    parameters=EmaComponent().parameter_schema.canonicalize(
                        {"period": fast_period}
                    ),
                    output_id=_EMA_VALUE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_EMA_ID,
                    parameters=EmaComponent().parameter_schema.canonicalize(
                        {"period": slow_period}
                    ),
                    output_id=_EMA_VALUE_OUTPUT,
                )
            ),
        )


class NumpyMacdImplementation:
    """NumPy MACD backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        fast_period = int(parameters.get("fast_period"))
        slow_period = int(parameters.get("slow_period"))
        signal_period = int(parameters.get("signal_period"))
        _validate_periods(fast_period, slow_period)
        bar_count = len(workspace.market)

        fast_result = _ema_result_for_period(workspace.dependency_results, period=fast_period)
        slow_result = _ema_result_for_period(workspace.dependency_results, period=slow_period)
        fast_values = np.asarray(fast_result.outputs[_EMA_VALUE_OUTPUT].values, dtype=np.float64)
        slow_values = np.asarray(slow_result.outputs[_EMA_VALUE_OUTPUT].values, dtype=np.float64)

        line = fast_values - slow_values

        # `line`'s own valid region starts once both EMAs are valid -- read
        # from the dependency results' own metadata rather than re-deriving
        # `period - 1` independently, so a change in `trend.ema`'s warmup
        # convention is picked up here automatically.
        line_valid_from = max(
            fast_result.validity.valid_from_index,
            slow_result.validity.valid_from_index,
        )

        signal = np.full(bar_count, np.nan, dtype=np.float64)
        valid_line = line[line_valid_from:]
        if valid_line.size > 0:
            signal[line_valid_from:] = ema(valid_line, signal_period)

        histogram = line - signal

        warmup_bars = line_valid_from + (signal_period - 1)

        outputs: dict[OutputId, OutputSeries] = {
            _LINE_OUTPUT: ndarray_to_output_series(line),
            _SIGNAL_OUTPUT: ndarray_to_output_series(signal),
            _HISTOGRAM_OUTPUT: ndarray_to_output_series(histogram),
        }
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


__all__ = ["MacdComponent", "NumpyMacdImplementation"]
