"""Volatility Range-Based Variance Market Analysis component."""

import numpy as np

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

_COMPONENT_ID = ComponentId("volatility.range_based_variance")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.range_based_variance")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_VALUE = OutputId("value")
_KNOWN_METHODS = ("parkinson", "garman_klass")
_PARKINSON_CONSTANT = 1.0 / (4.0 * np.log(2.0))
_GARMAN_KLASS_CLOSE_COEFFICIENT = 2.0 * np.log(2.0) - 1.0

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("method", ParameterType.STR, default="parkinson"),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class RangeBasedVarianceComponent:
    """Causal rolling volatility estimator using the bar's full range.

    More sample-efficient than a close-to-close estimator
    (``volatility.relative_volatility``) for the same window length,
    because it uses each bar's high/low (and, for ``"garman_klass"``,
    open/close too) instead of only the close.

    ``method="parkinson"`` (default): per-bar term
    ``ln(high / low) ** 2``, rolling-averaged over ``period`` bars and
    scaled by ``1 / (4 * ln(2))``; ``value`` is the square root (a
    volatility, not a variance, matching this catalog's other
    ``volatility.*`` components).

    ``method="garman_klass"``: per-bar term
    ``0.5 * ln(high / low) ** 2 - (2 * ln(2) - 1) * ln(close / open) ** 2``,
    same rolling average and square root. A negative rolling average (rare,
    theoretically possible for Garman-Klass on unusual bars) is clipped to
    ``0.0`` before the square root, not left as ``NaN``.

    Warm-up: ``period - 1`` bars. No true zero-denominator case: both
    formulas are log-ratios of always-positive prices, and a zero-range bar
    (``high == low``) simply contributes ``0.0`` -- a bar with genuinely no
    range carries no volatility, not an undefined value.
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
        method = str(parameters.get("method"))
        if method == "garman_klass":
            return (
                DataFieldDependency("open"),
                DataFieldDependency("high"),
                DataFieldDependency("low"),
                DataFieldDependency("close"),
            )
        return (DataFieldDependency("high"), DataFieldDependency("low"))

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


def _rolling_mean(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < period or period < 1:
        return out
    kernel = np.ones(period, dtype=np.float64) / period
    valid = np.convolve(values, kernel, mode="valid")
    out[period - 1 :] = valid
    return out


class NumpyRangeBasedVarianceImplementation:
    """NumPy Range-Based Variance backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        method = str(parameters.get("method"))
        if method not in _KNOWN_METHODS:
            msg = f"unknown method {method!r}; must be one of {_KNOWN_METHODS}"
            raise ComponentValidationError(_COMPONENT_ID, msg)

        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)

        high_low_term = np.log(high / low) ** 2
        if method == "garman_klass":
            open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
            close = np.asarray(workspace.market.close.values, dtype=np.float64)
            close_open_term = np.log(close / open_) ** 2
            per_bar = 0.5 * high_low_term - _GARMAN_KLASS_CLOSE_COEFFICIENT * close_open_term
        else:
            per_bar = _PARKINSON_CONSTANT * high_low_term

        rolling_variance = _rolling_mean(per_bar, period)
        value = np.sqrt(np.clip(rolling_variance, 0.0, None))

        outputs: dict[OutputId, OutputSeries] = {_VALUE: ndarray_to_output_series(value)}
        warmup_bars = max(period - 1, 0)
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
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NumpyRangeBasedVarianceImplementation", "RangeBasedVarianceComponent"]
