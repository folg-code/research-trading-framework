"""Volume Session Weighted Price Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.session_weighted_price import (
    session_weighted_price,
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

_COMPONENT_ID = ComponentId("volume.session_weighted_price")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.session_weighted_price")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_VALUE = OutputId("value")
_DEVIATION = OutputId("deviation")
_UPPER_BAND = OutputId("upper_band")
_LOWER_BAND = OutputId("lower_band")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("band_multiplier", ParameterType.FLOAT, default=2.0, minimum=0.0),)
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_VALUE, "float64"),
        OutputFieldSpec(_DEVIATION, "float64"),
        OutputFieldSpec(_UPPER_BAND, "float64"),
        OutputFieldSpec(_LOWER_BAND, "float64"),
    )
)


class SessionWeightedPriceComponent:
    """Causal session-anchored volume-weighted average price, plus deviation bands.

    IDEA-031's deferred session-anchored VWAP variant of
    ``volume.rolling_weighted_price``: accumulated from each RTH session's
    own start (per ``structure.session_range``'s exact session-boundary
    convention -- a new session starts at the first RTH bar of a trading
    day or the first RTH bar after a non-RTH gap), not a fixed rolling bar
    count. Outside RTH, every output is ``NaN`` (the session doesn't exist
    yet/has ended).

    ``typical_price = (high + low + close) / 3``. ``value`` is the
    session-so-far volume-weighted average of ``typical_price``;
    ``deviation`` is the session-so-far volume-weighted standard deviation
    of ``typical_price`` around that same ``value``; ``upper_band``/
    ``lower_band`` are ``value +/- band_multiplier * deviation``.

    Zero-volume convention: see
    :func:`trading_framework.market_analysis.adapters.numpy.session_weighted_price.session_weighted_price`
    -- a session with no volume at all so far leaves every output ``NaN``,
    the same deliberate divergence from this catalog's usual "0.0 on
    zero-denominator" convention as ``volume.rolling_weighted_price``,
    since these outputs are raw price levels, not ratios.

    No component dependency: computed directly from OHLCV and the trading
    session metadata (``is_rth``/``trading_day``) already resolved for the
    run. Warm-up: none in the usual bar-count sense -- every RTH bar is
    valid from its own session's first bar; outside RTH bars are NaN by
    definition, not by warm-up.
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


class NumpySessionWeightedPriceImplementation:
    """NumPy Session Weighted Price backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        band_multiplier = float(parameters.get("band_multiplier"))

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

        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)
        volume = np.asarray(workspace.market.volume.values, dtype=np.float64)
        typical_price = (high + low + close) / 3.0

        arrays = session_weighted_price(
            typical_price,
            volume,
            is_rth=np.asarray(metadata.is_rth, dtype=bool),
            trading_day_ordinal=np.array(
                [day.toordinal() for day in metadata.trading_days],
                dtype=np.int32,
            ),
            band_multiplier=band_multiplier,
        )

        outputs: dict[OutputId, OutputSeries] = {
            _VALUE: ndarray_to_output_series(arrays.value),
            _DEVIATION: ndarray_to_output_series(arrays.deviation),
            _UPPER_BAND: ndarray_to_output_series(arrays.upper_band),
            _LOWER_BAND: ndarray_to_output_series(arrays.lower_band),
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


__all__ = ["NumpySessionWeightedPriceImplementation", "SessionWeightedPriceComponent"]
