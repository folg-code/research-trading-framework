"""Statistics Rolling Window Position Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    dependency_results_values,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.rolling_window_position import (
    rolling_window_position,
)
from trading_framework.market_analysis.components.volatility.atr import AtrComponent
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

_COMPONENT_ID = ComponentId("statistics.rolling_window_position")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.rolling_window_position")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")
_KNOWN_METHODS = ("normal", "empirical")

_Z_SCORE = OutputId("z_score")
_PERCENTILE = OutputId("percentile")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("source_period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("window", ParameterType.INT, default=20, minimum=2),
        ParameterFieldSpec("method", ParameterType.STR, default="normal"),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_Z_SCORE, "float64"),
        OutputFieldSpec(_PERCENTILE, "float64"),
    )
)


class RollingWindowPositionComponent:
    """Causal position of another component's output within its own rolling window.

    Per IDEA-030: a generic building block for turning any continuous
    component output into a state classifier, instead of hand-writing a
    bespoke percentile-window for each one. This v1 depends on
    ``volatility.atr`` (keyed by ``source_period``) as its input series --
    the same fixed-target-dependency pattern already used by
    ``momentum.macd``/``trend.ema_distance``/``volatility.regime_state`` --
    demonstrating the composition; a future caller wanting a different
    source swaps this component's own dependency, the registry/DSL layer
    already supports a component depending on any other component's output
    (Phase 19 Wave 0 resolution, no new registry capability needed).

    ``z_score[i] = (source[i] - mean(source, window)[i]) /
    stdev(source, window)[i]`` (population stdev). ``percentile`` is kept
    as an explicit, separate value from ``z_score`` per ``method`` (the
    source material conflated these under one field name):

    - ``"normal"`` (default): the standard-normal CDF of ``z_score``.
    - ``"empirical"``: the fraction of the window's own values that are
      ``<= source[i]`` (an inclusive rolling rank, no distributional
      assumption).

    Zero-variance convention: a perfectly flat window defines ``z_score =
    0.0`` (this catalog's ordinary zero-denominator convention) rather than
    ``NaN`` -- the value trivially equals its own window mean. Warm-up:
    the source ATR's own ``valid_from_index`` plus ``window - 1`` further
    bars.
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
        source_period = int(parameters.get("source_period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize(
                        {"period": source_period}
                    ),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyRollingWindowPositionImplementation:
    """NumPy Rolling Window Position backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        window = int(parameters.get("window"))
        method = str(parameters.get("method"))
        if method not in _KNOWN_METHODS:
            msg = f"unknown method {method!r}; must be one of {_KNOWN_METHODS}"
            raise ComponentValidationError(_COMPONENT_ID, msg)
        bar_count = len(workspace.market)

        source_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )
        source_result = next(iter(workspace.dependency_results.values()))
        arrays = rolling_window_position(source_values, window=window, method=method)

        # The kernel's own NaN handling only covers its own window boundary
        # (`window - 1`); it does not know about the source series' own
        # upstream warmup (`source_result.validity.valid_from_index`), and
        # the "empirical" method's `<=` comparisons would otherwise treat a
        # NaN source value as neither less-nor-greater rather than
        # propagating NaN. Mask explicitly to the full warmup instead of
        # relying on kernel-internal propagation for this case.
        z_score = np.asarray(arrays.z_score, dtype=np.float64)
        percentile = np.asarray(arrays.percentile, dtype=np.float64)
        warmup_bars = source_result.validity.valid_from_index + (window - 1)
        z_score[:warmup_bars] = np.nan
        percentile[:warmup_bars] = np.nan

        outputs: dict[OutputId, OutputSeries] = {
            _Z_SCORE: ndarray_to_output_series(z_score),
            _PERCENTILE: ndarray_to_output_series(percentile),
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


__all__ = ["NumpyRollingWindowPositionImplementation", "RollingWindowPositionComponent"]
