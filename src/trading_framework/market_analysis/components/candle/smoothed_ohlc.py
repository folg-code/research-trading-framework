"""Candle Smoothed OHLC Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.smoothed_ohlc import smoothed_ohlc
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
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("candle.smoothed_ohlc")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.smoothed_ohlc")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_OPEN = OutputId("open")
_HIGH = OutputId("high")
_LOW = OutputId("low")
_CLOSE = OutputId("close")

_PARAMETER_SCHEMA = ParameterSchema(fields=())
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_OPEN, "float64"),
        OutputFieldSpec(_HIGH, "float64"),
        OutputFieldSpec(_LOW, "float64"),
        OutputFieldSpec(_CLOSE, "float64"),
    )
)


class SmoothedOhlcComponent:
    """Causal smoothed-OHLC ("Heikin-Ashi") transform of the bar series.

    ``close = (open + high + low + close) / 4``; ``open`` recurses from the
    prior bar's own smoothed open/close (seeded at bar 0 as
    ``(open[0] + close[0]) / 2``); ``high``/``low`` are the raw bar's own
    high/low widened (never narrowed) to also contain the smoothed
    open/close. Fully causal and recursively defined from bar 0 -- no
    external period parameter, so ``bars_before = 0`` and there is no
    warm-up: every bar is valid the moment its own raw OHLC exists.
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


class NumpySmoothedOhlcImplementation:
    """NumPy Smoothed OHLC backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        bar_count = len(workspace.market)
        open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        arrays = smoothed_ohlc(open_, high, low, close)

        outputs: dict[OutputId, OutputSeries] = {
            _OPEN: ndarray_to_output_series(arrays.open),
            _HIGH: ndarray_to_output_series(arrays.high),
            _LOW: ndarray_to_output_series(arrays.low),
            _CLOSE: ndarray_to_output_series(arrays.close),
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


__all__ = ["NumpySmoothedOhlcImplementation", "SmoothedOhlcComponent"]
