"""Structure Distance To Level Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.session.previous_period_extreme import (
    PreviousPeriodExtremeComponent,
)
from trading_framework.market_analysis.components.structure.matched_extreme_pair import (
    MatchedExtremePairComponent,
)
from trading_framework.market_analysis.components.structure.session_range import (
    SessionRangeComponent,
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

_COMPONENT_ID = ComponentId("structure.distance_to_level")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.distance_to_level")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SESSION_RANGE_ID = ComponentId("structure.session_range")
_PREVIOUS_PERIOD_EXTREME_ID = ComponentId("session.previous_period_extreme")
_MATCHED_EXTREME_PAIR_ID = ComponentId("structure.matched_extreme_pair")
_ATR_ID = ComponentId("volatility.atr")

_SESSION_HIGH_OUTPUT = OutputId("session_high")
_SESSION_LOW_OUTPUT = OutputId("session_low")
_PREVIOUS_PERIOD_VALUE_OUTPUT = OutputId("value")
_LATEST_MATCHED_HIGH_LEVEL = OutputId("latest_matched_high_level")
_LATEST_MATCHED_LOW_LEVEL = OutputId("latest_matched_low_level")
_ATR_VALUE_OUTPUT = OutputId("value")

_DISTANCE_TO_SESSION_HIGH = OutputId("distance_to_session_high_atr")
_DISTANCE_TO_SESSION_LOW = OutputId("distance_to_session_low_atr")
_DISTANCE_TO_PREVIOUS_DAY_HIGH = OutputId("distance_to_previous_day_high_atr")
_DISTANCE_TO_PREVIOUS_DAY_LOW = OutputId("distance_to_previous_day_low_atr")
_DISTANCE_TO_MATCHED_EXTREME_PAIR_HIGH = OutputId("distance_to_matched_extreme_pair_high_atr")
_DISTANCE_TO_MATCHED_EXTREME_PAIR_LOW = OutputId("distance_to_matched_extreme_pair_low_atr")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("tolerance_atr_multiple", ParameterType.FLOAT, default=0.1, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_DISTANCE_TO_SESSION_HIGH, "float64"),
        OutputFieldSpec(_DISTANCE_TO_SESSION_LOW, "float64"),
        OutputFieldSpec(_DISTANCE_TO_PREVIOUS_DAY_HIGH, "float64"),
        OutputFieldSpec(_DISTANCE_TO_PREVIOUS_DAY_LOW, "float64"),
        OutputFieldSpec(_DISTANCE_TO_MATCHED_EXTREME_PAIR_HIGH, "float64"),
        OutputFieldSpec(_DISTANCE_TO_MATCHED_EXTREME_PAIR_LOW, "float64"),
    )
)


def _dependency_result_for(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    component_id: ComponentId,
    parameters: Mapping[str, object] | None = None,
) -> AnalysisResult:
    for result in dependency_results.values():
        identity = result.computation_identity
        if identity.component_id != component_id:
            continue
        if parameters is None:
            return result
        if all(identity.parameters.get(key) == value for key, value in parameters.items()):
            return result
    raise ComponentValidationError(
        _COMPONENT_ID,
        f"missing dependency result for {component_id} {parameters or ''}",
    )


class DistanceToLevelComponent:
    """ATR-normalized causal distance to every configured level source (IDEA-032, D-P19-03).

    Generalizes ``structure.level_distance`` (kept exactly as-is, single
    source) to six level sources, always reported together as fixed named
    fields -- **not** a caller-configurable ``level_sources`` subset as
    D-P19-03 originally proposed. Architecture triage found the registry
    has no mechanism for a component's ``OutputSchema`` to vary per
    ``ComponentRequest``: every component is registered as a single
    singleton instance per ``component_id``
    (``ComponentRegistry.register``), and ``output_schema`` is a plain
    property with no access to a request's parameters -- there is nowhere
    for a "sized by `level_sources`" schema to live. All six fields are
    therefore always declared and always computed; this still delivers
    IDEA-032's actual goal (one place with fixed named fields per source,
    not several near-duplicate distance components) within what the
    registry can do.

    ``distance_to_<source>_atr = (source_high - close) / atr`` for a
    "high" source, ``(close - source_low) / atr`` for a "low" source --
    the same sign convention as ``structure.level_distance``. The six
    sources: ``session_high``/``session_low`` (``structure.session_range``,
    the *running*, not final, session extreme), ``previous_day_high``/
    ``previous_day_low`` (``session.previous_period_extreme(period="day",
    ...)``), and ``matched_extreme_pair_high``/``matched_extreme_pair_low``
    (``structure.matched_extreme_pair``'s ``latest_matched_*_level``
    outputs, added in this same task -- see that component's own
    docstring).

    Zero-denominator convention: this catalog's ordinary convention
    (D-S048-10) -- ``atr == 0.0`` defines a distance as ``0.0`` rather than
    an incidental ``inf``/``NaN``, but ONLY when the level itself is a real
    number. A ``NaN`` level (no previous day has closed yet, no match has
    occurred yet, outside the running session) stays ``NaN`` regardless of
    ATR -- "no level to measure against" is not the same case as "a real
    level, on a zero-ATR bar," and must not be conflated into a fabricated
    ``0.0``.

    Depends on ``structure.session_range`` (no parameters), two
    ``session.previous_period_extreme`` outputs (``period="day"``,
    ``side="high"``/``"low"``), ``structure.matched_extreme_pair`` (keyed
    by ``pivot_range``/``period``/``tolerance_atr_multiple``), and
    ``volatility.atr`` (keyed by ``period``). Warm-up: the latest of all
    five dependencies' own ``valid_from_index``.
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
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        pivot_range = int(parameters.get("pivot_range"))
        tolerance_atr_multiple = float(parameters.get("tolerance_atr_multiple"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SESSION_RANGE_ID,
                    parameters=SessionRangeComponent().parameter_schema.canonicalize({}),
                    output_id=_SESSION_HIGH_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_PREVIOUS_PERIOD_EXTREME_ID,
                    parameters=PreviousPeriodExtremeComponent().parameter_schema.canonicalize(
                        {"period": "day", "side": "high"}
                    ),
                    output_id=_PREVIOUS_PERIOD_VALUE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_PREVIOUS_PERIOD_EXTREME_ID,
                    parameters=PreviousPeriodExtremeComponent().parameter_schema.canonicalize(
                        {"period": "day", "side": "low"}
                    ),
                    output_id=_PREVIOUS_PERIOD_VALUE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_MATCHED_EXTREME_PAIR_ID,
                    parameters=MatchedExtremePairComponent().parameter_schema.canonicalize(
                        {
                            "pivot_range": pivot_range,
                            "period": period,
                            "tolerance_atr_multiple": tolerance_atr_multiple,
                        }
                    ),
                    output_id=_LATEST_MATCHED_HIGH_LEVEL,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": period}),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyDistanceToLevelImplementation:
    """NumPy Distance To Level backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        session_result = _dependency_result_for(
            workspace.dependency_results, component_id=_SESSION_RANGE_ID
        )
        previous_day_high_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_PREVIOUS_PERIOD_EXTREME_ID,
            parameters={"side": "high"},
        )
        previous_day_low_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_PREVIOUS_PERIOD_EXTREME_ID,
            parameters={"side": "low"},
        )
        matched_result = _dependency_result_for(
            workspace.dependency_results, component_id=_MATCHED_EXTREME_PAIR_ID
        )
        atr_result = _dependency_result_for(workspace.dependency_results, component_id=_ATR_ID)

        session_high = np.asarray(
            session_result.outputs[_SESSION_HIGH_OUTPUT].values, dtype=np.float64
        )
        session_low = np.asarray(
            session_result.outputs[_SESSION_LOW_OUTPUT].values, dtype=np.float64
        )
        previous_day_high = np.asarray(
            previous_day_high_result.outputs[_PREVIOUS_PERIOD_VALUE_OUTPUT].values,
            dtype=np.float64,
        )
        previous_day_low = np.asarray(
            previous_day_low_result.outputs[_PREVIOUS_PERIOD_VALUE_OUTPUT].values,
            dtype=np.float64,
        )
        matched_high_level = np.asarray(
            matched_result.outputs[_LATEST_MATCHED_HIGH_LEVEL].values, dtype=np.float64
        )
        matched_low_level = np.asarray(
            matched_result.outputs[_LATEST_MATCHED_LOW_LEVEL].values, dtype=np.float64
        )
        atr_values = np.asarray(atr_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        def _distance(level: np.ndarray, *, level_is_high_side: bool) -> np.ndarray:
            # A NaN level (no previous day yet, no match yet, outside the
            # session) must stay NaN regardless of ATR -- "no level" is not
            # the same case as "a real level, zero-ATR window," so the
            # zero-denominator override below only applies when the level
            # itself is a real number.
            raw = (level - close) if level_is_high_side else (close - level)
            with np.errstate(divide="ignore", invalid="ignore"):
                raw = raw / atr_values
            atr_is_zero_with_real_level = (atr_values == 0.0) & ~np.isnan(level)
            result: np.ndarray = np.where(atr_is_zero_with_real_level, 0.0, raw)
            return result

        distance_to_session_high = _distance(session_high, level_is_high_side=True)
        distance_to_session_low = _distance(session_low, level_is_high_side=False)
        distance_to_previous_day_high = _distance(previous_day_high, level_is_high_side=True)
        distance_to_previous_day_low = _distance(previous_day_low, level_is_high_side=False)
        distance_to_matched_high = _distance(matched_high_level, level_is_high_side=True)
        distance_to_matched_low = _distance(matched_low_level, level_is_high_side=False)

        outputs: dict[OutputId, OutputSeries] = {
            _DISTANCE_TO_SESSION_HIGH: ndarray_to_output_series(distance_to_session_high),
            _DISTANCE_TO_SESSION_LOW: ndarray_to_output_series(distance_to_session_low),
            _DISTANCE_TO_PREVIOUS_DAY_HIGH: ndarray_to_output_series(distance_to_previous_day_high),
            _DISTANCE_TO_PREVIOUS_DAY_LOW: ndarray_to_output_series(distance_to_previous_day_low),
            _DISTANCE_TO_MATCHED_EXTREME_PAIR_HIGH: ndarray_to_output_series(
                distance_to_matched_high
            ),
            _DISTANCE_TO_MATCHED_EXTREME_PAIR_LOW: ndarray_to_output_series(
                distance_to_matched_low
            ),
        }
        warmup_bars = max(
            session_result.validity.valid_from_index,
            previous_day_high_result.validity.valid_from_index,
            previous_day_low_result.validity.valid_from_index,
            matched_result.validity.valid_from_index,
            atr_result.validity.valid_from_index,
        )
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


__all__ = ["DistanceToLevelComponent", "NumpyDistanceToLevelImplementation"]
