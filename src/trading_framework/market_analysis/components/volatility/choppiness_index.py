"""Volatility Choppiness Index Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import rolling_max, rolling_min, sma
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    dependency_results_values,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.volatility.true_range import TrueRangeComponent
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
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.choppiness_index")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.choppiness_index")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_TRUE_RANGE_ID = ComponentId("volatility.true_range")
_TRUE_RANGE_OUTPUT = OutputId("value")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=2),)
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class ChoppinessIndexComponent:
    """Causal standard Choppiness Index: range-bound vs. trending conditions.

    ``value = 100 * log10(sum(true_range, period) / (max(high, period) -
    min(low, period))) / log10(period)`` -- a high value (near 100) means
    the period's total true-range "path length" is close to its net
    high/low range (choppy, range-bound); a low value (near 0) means the
    path length greatly exceeds the net range (a sustained, directional
    trend).

    ``period`` requires ``minimum=2`` -- ``log10(1) == 0.0`` would make the
    formula's denominator zero regardless of the price data, not a genuine
    zero-denominator market condition.

    Zero-denominator convention: a perfectly flat window
    (``max(high) == min(low)``) forces every bar's true range to ``0.0``
    too, so both the numerator and denominator vanish together; this is
    this catalog's ORDINARY zero-denominator case, defined as ``0.0``, not
    an inf/NaN.

    Depends on ``volatility.true_range`` (no parameters) for the shared TR
    formula; ``max(high)``/``min(low)`` are computed directly since they
    are plain kernel calls, not dependency-worthy on their own. Warm-up:
    ``period - 1`` bars.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        return HistoryRequirement(bars_before=max(period - 1, 0))

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("high"),
            DataFieldDependency("low"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_TRUE_RANGE_ID,
                    parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
                    output_id=_TRUE_RANGE_OUTPUT,
                )
            ),
        )


class NumpyChoppinessIndexImplementation:
    """NumPy Choppiness Index backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)

        tr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_TRUE_RANGE_OUTPUT,
        )
        sum_true_range = sma(tr_values, period) * period
        highest = rolling_max(high, period)
        lowest = rolling_min(low, period)
        denominator = highest - lowest

        with np.errstate(divide="ignore", invalid="ignore"):
            value = np.where(
                denominator == 0.0,
                0.0,
                100.0 * np.log10(sum_true_range / denominator) / np.log10(period),
            )
        warmup_bars = max(period - 1, 0)
        value[:warmup_bars] = np.nan

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
            outputs={_VALUE: ndarray_to_output_series(value)},
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["ChoppinessIndexComponent", "NumpyChoppinessIndexImplementation"]
