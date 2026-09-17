"""Volume Rolling Weighted Price Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.rolling_weighted_price import (
    rolling_weighted_price,
)
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

_COMPONENT_ID = ComponentId("volume.rolling_weighted_price")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.rolling_weighted_price")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_VALUE = OutputId("value")
_DEVIATION = OutputId("deviation")
_UPPER_BAND = OutputId("upper_band")
_LOWER_BAND = OutputId("lower_band")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("band_multiplier", ParameterType.FLOAT, default=2.0, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_VALUE, "float64"),
        OutputFieldSpec(_DEVIATION, "float64"),
        OutputFieldSpec(_UPPER_BAND, "float64"),
        OutputFieldSpec(_LOWER_BAND, "float64"),
    )
)


class RollingWeightedPriceComponent:
    """Causal rolling volume-weighted average price, plus deviation bands.

    A fixed ``period``-bar rolling window only -- explicitly NOT a
    session-anchored VWAP (that has its own lookahead/anchoring questions,
    deferred to Wave B per the PRD). ``typical_price = (high + low +
    close) / 3``. ``value`` is the volume-weighted average of
    ``typical_price`` over the window; ``deviation`` is the volume-weighted
    standard deviation of ``typical_price`` around that same ``value``;
    ``upper_band``/``lower_band`` are ``value +/- band_multiplier *
    deviation``.

    Zero-volume-window convention: see
    :func:`trading_framework.market_analysis.adapters.numpy.rolling_weighted_price.rolling_weighted_price`
    -- a window with no volume at all leaves every output ``NaN``
    (a deliberate divergence from this catalog's usual "0.0 on
    zero-denominator" convention, since these outputs are raw price
    levels, not ratios).

    No dependency: computed directly from OHLCV. Warm-up: ``period - 1``
    bars.
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
            DataFieldDependency("close"),
            DataFieldDependency("volume"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyRollingWeightedPriceImplementation:
    """NumPy Rolling Weighted Price backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        band_multiplier = float(parameters.get("band_multiplier"))
        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)
        volume = np.asarray(workspace.market.volume.values, dtype=np.float64)

        typical_price = (high + low + close) / 3.0
        arrays = rolling_weighted_price(
            typical_price, volume, period=period, band_multiplier=band_multiplier
        )

        outputs: dict[OutputId, OutputSeries] = {
            _VALUE: ndarray_to_output_series(arrays.value),
            _DEVIATION: ndarray_to_output_series(arrays.deviation),
            _UPPER_BAND: ndarray_to_output_series(arrays.upper_band),
            _LOWER_BAND: ndarray_to_output_series(arrays.lower_band),
        }
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


__all__ = ["NumpyRollingWeightedPriceImplementation", "RollingWeightedPriceComponent"]
