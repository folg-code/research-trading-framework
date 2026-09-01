"""Candle Wick Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.candle_wick import candle_wick
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
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
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("candle.wick")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.candle_wick")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_UPPER_WICK_RATIO = OutputId("upper_wick_ratio")
_LOWER_WICK_RATIO = OutputId("lower_wick_ratio")
_BODY_RATIO = OutputId("body_ratio")

_PARAMETER_SCHEMA = ParameterSchema(fields=())
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_UPPER_WICK_RATIO, "float64"),
        OutputFieldSpec(_LOWER_WICK_RATIO, "float64"),
        OutputFieldSpec(_BODY_RATIO, "float64"),
    )
)


class CandleWickComponent:
    """Bar-local upper/lower wick and body ratios of the bar's own range.

    Causal and history-free: every output depends only on the current bar's
    OHLC, so ``bars_before = 0``. A zero-range bar (``high == low``) is a
    documented, defined case -- see
    :func:`trading_framework.market_analysis.adapters.numpy.candle_wick.candle_wick`
    for the exact convention (all three ratios are ``0.0``), not an
    incidental ``NaN``.
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


class NumpyCandleWickImplementation:
    """NumPy candle wick/body ratio backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        market = workspace.market
        bar_count = len(market)
        open_ = np.asarray(market.open.values, dtype=np.float64)
        high = np.asarray(market.high.values, dtype=np.float64)
        low = np.asarray(market.low.values, dtype=np.float64)
        close = np.asarray(market.close.values, dtype=np.float64)
        arrays = candle_wick(open_, high, low, close)
        outputs: dict[OutputId, OutputSeries] = {
            _UPPER_WICK_RATIO: ndarray_to_output_series(arrays.upper_wick_ratio),
            _LOWER_WICK_RATIO: ndarray_to_output_series(arrays.lower_wick_ratio),
            _BODY_RATIO: ndarray_to_output_series(arrays.body_ratio),
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


__all__ = ["CandleWickComponent", "NumpyCandleWickImplementation"]
