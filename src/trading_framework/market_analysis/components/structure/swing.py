"""Swing Structure Market Analysis component."""

from __future__ import annotations

from datetime import datetime

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    derive_available_at_timestamps,
)
from trading_framework.market_analysis.adapters.numpy.swing import (
    SwingStructureResult,
    detect_swing_structure,
)
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.availability import (
    AvailabilityMetadata,
    AvailabilityPolicy,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement, WarmUpMetadata
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.lineage import Lineage
from trading_framework.market_analysis.models.outputs import (
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import (
    AnalysisResult,
    OutputSeries,
    ValidityMetadata,
)
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("structure.swing")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.swing_structure")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_HIGH_EVENT = OutputId("swing_high_event")
_SWING_LOW_EVENT = OutputId("swing_low_event")
_SWING_HIGH_PRICE = OutputId("swing_high_price")
_SWING_LOW_PRICE = OutputId("swing_low_price")
_SWING_HIGH_OBSERVED_INDEX = OutputId("swing_high_observed_index")
_SWING_LOW_OBSERVED_INDEX = OutputId("swing_low_observed_index")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")
_LATEST_SWING_HIGH_OBSERVED_INDEX = OutputId("latest_swing_high_observed_index")
_LATEST_SWING_LOW_OBSERVED_INDEX = OutputId("latest_swing_low_observed_index")
_HIGHER_HIGH_EVENT = OutputId("higher_high_event")
_LOWER_HIGH_EVENT = OutputId("lower_high_event")
_HIGHER_LOW_EVENT = OutputId("higher_low_event")
_LOWER_LOW_EVENT = OutputId("lower_low_event")
_LATEST_HIGHER_HIGH_LEVEL = OutputId("latest_higher_high_level")
_LATEST_LOWER_HIGH_LEVEL = OutputId("latest_lower_high_level")
_LATEST_HIGHER_LOW_LEVEL = OutputId("latest_higher_low_level")
_LATEST_LOWER_LOW_LEVEL = OutputId("latest_lower_low_level")
_LATEST_HIGHER_HIGH_OBSERVED_INDEX = OutputId("latest_higher_high_observed_index")
_LATEST_LOWER_HIGH_OBSERVED_INDEX = OutputId("latest_lower_high_observed_index")
_LATEST_HIGHER_LOW_OBSERVED_INDEX = OutputId("latest_higher_low_observed_index")
_LATEST_LOWER_LOW_OBSERVED_INDEX = OutputId("latest_lower_low_observed_index")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),)
)
_EVENT_ALIGNMENT = AlignmentPolicy.EVENT_AT_AVAILABLE


def _event_output(output_id: OutputId) -> OutputFieldSpec:
    return OutputFieldSpec(
        output_id,
        "float64",
        group=OutputGroup.CORE,
        alignment_policy=_EVENT_ALIGNMENT,
    )


def _state_output(output_id: OutputId) -> OutputFieldSpec:
    return OutputFieldSpec(output_id, "float64", group=OutputGroup.CORE)


_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        _event_output(_SWING_HIGH_EVENT),
        _event_output(_SWING_LOW_EVENT),
        _event_output(_SWING_HIGH_PRICE),
        _event_output(_SWING_LOW_PRICE),
        _event_output(_SWING_HIGH_OBSERVED_INDEX),
        _event_output(_SWING_LOW_OBSERVED_INDEX),
        _state_output(_LATEST_SWING_HIGH_LEVEL),
        _state_output(_LATEST_SWING_LOW_LEVEL),
        _state_output(_LATEST_SWING_HIGH_OBSERVED_INDEX),
        _state_output(_LATEST_SWING_LOW_OBSERVED_INDEX),
        _event_output(_HIGHER_HIGH_EVENT),
        _event_output(_LOWER_HIGH_EVENT),
        _event_output(_HIGHER_LOW_EVENT),
        _event_output(_LOWER_LOW_EVENT),
        _state_output(_LATEST_HIGHER_HIGH_LEVEL),
        _state_output(_LATEST_LOWER_HIGH_LEVEL),
        _state_output(_LATEST_HIGHER_LOW_LEVEL),
        _state_output(_LATEST_LOWER_LOW_LEVEL),
        _state_output(_LATEST_HIGHER_HIGH_OBSERVED_INDEX),
        _state_output(_LATEST_LOWER_HIGH_OBSERVED_INDEX),
        _state_output(_LATEST_HIGHER_LOW_OBSERVED_INDEX),
        _state_output(_LATEST_LOWER_LOW_OBSERVED_INDEX),
    )
)


class SwingStructureComponent:
    """Right-window swing structure with explicit event/state outputs.

    Swing points are confirmed on the available index (detection bar) using a
    right-side confirmation window only. This is not a symmetric local-extrema
    (classic pivot) detector. Results are never back-written to the observed index.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.STRUCTURE
    causality = Causality.DELAYED
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        pivot_range = int(parameters.get("pivot_range"))
        return HistoryRequirement(bars_before=pivot_range)

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
        return ()


def _series_with_availability(
    values: np.ndarray,
    *,
    available_at: tuple[datetime, ...],
) -> OutputSeries:
    return OutputSeries(
        values=tuple(float(value) for value in values),
        available_at=available_at,
    )


def _build_outputs(
    detected: SwingStructureResult,
    *,
    available_at: tuple[datetime, ...],
) -> dict[OutputId, OutputSeries]:
    mapping: dict[OutputId, np.ndarray] = {
        _SWING_HIGH_EVENT: detected.swing_high_event,
        _SWING_LOW_EVENT: detected.swing_low_event,
        _SWING_HIGH_PRICE: detected.swing_high_price,
        _SWING_LOW_PRICE: detected.swing_low_price,
        _SWING_HIGH_OBSERVED_INDEX: detected.swing_high_observed_index,
        _SWING_LOW_OBSERVED_INDEX: detected.swing_low_observed_index,
        _LATEST_SWING_HIGH_LEVEL: detected.latest_swing_high_level,
        _LATEST_SWING_LOW_LEVEL: detected.latest_swing_low_level,
        _LATEST_SWING_HIGH_OBSERVED_INDEX: detected.latest_swing_high_observed_index,
        _LATEST_SWING_LOW_OBSERVED_INDEX: detected.latest_swing_low_observed_index,
        _HIGHER_HIGH_EVENT: detected.higher_high_event,
        _LOWER_HIGH_EVENT: detected.lower_high_event,
        _HIGHER_LOW_EVENT: detected.higher_low_event,
        _LOWER_LOW_EVENT: detected.lower_low_event,
        _LATEST_HIGHER_HIGH_LEVEL: detected.latest_higher_high_level,
        _LATEST_LOWER_HIGH_LEVEL: detected.latest_lower_high_level,
        _LATEST_HIGHER_LOW_LEVEL: detected.latest_higher_low_level,
        _LATEST_LOWER_LOW_LEVEL: detected.latest_lower_low_level,
        _LATEST_HIGHER_HIGH_OBSERVED_INDEX: detected.latest_higher_high_observed_index,
        _LATEST_LOWER_HIGH_OBSERVED_INDEX: detected.latest_lower_high_observed_index,
        _LATEST_HIGHER_LOW_OBSERVED_INDEX: detected.latest_higher_low_observed_index,
        _LATEST_LOWER_LOW_OBSERVED_INDEX: detected.latest_lower_low_observed_index,
    }
    outputs: dict[OutputId, OutputSeries] = {}
    for output_id, values in mapping.items():
        outputs[output_id] = _series_with_availability(values, available_at=available_at)
    return outputs


class NumpySwingStructureImplementation:
    """NumPy swing structure backend (reference loop; Numba-ready)."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        pivot_range = int(parameters.get("pivot_range"))
        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        detected = detect_swing_structure(high, low, pivot_range=pivot_range)

        if workspace.planned_computation_identity is not None:
            identity = workspace.planned_computation_identity
            computation_timeframe = identity.computation_timeframe
        else:
            computation_timeframe = (
                workspace.computation_timeframe
                if workspace.computation_timeframe
                else context.timeframe
            )
            identity = ComputationIdentity(
                component_id=_COMPONENT_ID,
                component_version=_COMPONENT_VERSION,
                implementation_id=_IMPLEMENTATION_ID,
                implementation_version=_IMPLEMENTATION_VERSION,
                parameters=parameters,
                dataset_ref=context.dataset_ref,
                computation_timeframe=computation_timeframe,
                requested_range=context.requested_range,
                dependency_keys=(),
                input_identity_key=workspace.input_identity_key,
            )

        available_at = derive_available_at_timestamps(
            workspace.market.timestamps,
            computation_timeframe,
        )
        outputs = _build_outputs(detected, available_at=available_at)

        valid_from_index = pivot_range
        valid_to_index = max(valid_from_index, bar_count - 1)
        return AnalysisResult(
            computation_identity=identity,
            output_schema=_OUTPUT_SCHEMA,
            outputs=outputs,
            lineage=Lineage(
                dataset_ref=context.dataset_ref,
                component_id=_COMPONENT_ID,
                component_version=_COMPONENT_VERSION,
                implementation_id=_IMPLEMENTATION_ID,
                implementation_version=_IMPLEMENTATION_VERSION,
                parameters=parameters,
                dependency_keys=(),
                engine_version=context.engine_version,
                executed_at=context.requested_range.end,
            ),
            validity=ValidityMetadata(
                valid_from_index=valid_from_index,
                valid_to_index=valid_to_index,
            ),
            warmup=WarmUpMetadata(
                warmup_bars=pivot_range,
                valid_from_index=valid_from_index,
                valid_to_index=valid_to_index,
            ),
            availability=AvailabilityMetadata(
                policy=AvailabilityPolicy.DELAYED_BARS,
                delay_bars=pivot_range,
            ),
            diagnostics={},
        )


__all__ = ["NumpySwingStructureImplementation", "SwingStructureComponent"]
