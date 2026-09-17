"""Structure Opening Gap Market Analysis component."""

import numpy as np

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

_COMPONENT_ID = ComponentId("structure.opening_gap")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.opening_gap")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")

_GAP_ATR = OutputId("gap_atr")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),)
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_GAP_ATR, "float64"),))
_WARMUP_BARS = 1


class OpeningGapComponent:
    """ATR-normalized causal gap between a bar's open and the prior bar's close.

    ``gap_atr = (open - prior_close) / atr``

    Distinct from ``structure.range_discontinuity``, which is a three-bar
    range gap, not an open-vs-prior-close gap. Positive values indicate a gap
    up, negative a gap down.

    Depends on ``volatility.atr`` for the normalizer, keyed by the same
    ``period`` parameter -- same dependency pattern as
    ``structure.level_distance``. Warmup inherits the wider of this
    component's own one-bar prior-close lookback and the ATR period: outputs
    are undefined (``NaN``) before ``max(1, period - 1)`` bars. The first bar
    has no real prior close; per this framework's ``true_range`` convention,
    it computes as if the prior close equals the bar's own close (an
    ``open - close`` value, not a true gap) rather than a synthetic zero --
    this is masked by warmup regardless, since ``period - 1 >= 1`` for any
    valid ATR period. A zero ATR (flat market) divides through to ``inf``/
    ``-inf``/``nan``, the same ordinary zero-denominator convention already
    used by ``structure.level_distance`` -- not special-cased.
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
        return (DataFieldDependency("open"), DataFieldDependency("close"))

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


class NumpyOpeningGapImplementation:
    """NumPy Opening Gap backend."""

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
        open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]

        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )

        with np.errstate(divide="ignore", invalid="ignore"):
            gap_atr = (open_ - prev_close) / atr_values

        outputs: dict[OutputId, OutputSeries] = {
            _GAP_ATR: ndarray_to_output_series(gap_atr),
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


__all__ = ["NumpyOpeningGapImplementation", "OpeningGapComponent"]
