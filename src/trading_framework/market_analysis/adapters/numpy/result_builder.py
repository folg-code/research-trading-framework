"""Helpers to build ``AnalysisResult`` from NumPy adapter outputs."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.availability import (
    AvailabilityMetadata,
    AvailabilityPolicy,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.history import WarmUpMetadata
from trading_framework.market_analysis.models.lineage import Lineage
from trading_framework.market_analysis.models.outputs import OutputId, OutputSchema
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.result import (
    AnalysisResult,
    OutputSeries,
    ValidityMetadata,
)


def ndarray_to_output_series(values: np.ndarray, *, dtype: str = "float64") -> OutputSeries:
    return OutputSeries(values=tuple(float(value) for value in values), dtype=dtype)


def build_analysis_result(
    *,
    context: AnalysisContext,
    component_id: ComponentId,
    component_version: ComponentVersion,
    implementation_id: ImplementationId,
    implementation_version: ImplementationVersion,
    parameters: CanonicalParameters,
    dependency_keys: tuple[str, ...],
    output_schema: OutputSchema,
    outputs: Mapping[OutputId, OutputSeries],
    warmup_bars: int,
    valid_from_index: int,
    bar_count: int,
) -> AnalysisResult:
    identity = ComputationIdentity(
        component_id=component_id,
        component_version=component_version,
        implementation_id=implementation_id,
        implementation_version=implementation_version,
        parameters=parameters,
        dataset_ref=context.dataset_ref,
        computation_timeframe=context.timeframe,
        requested_range=context.requested_range,
        dependency_keys=dependency_keys,
    )
    valid_to_index = max(valid_from_index, bar_count - 1)
    return AnalysisResult(
        computation_identity=identity,
        output_schema=output_schema,
        outputs=outputs,
        lineage=Lineage(
            dataset_ref=context.dataset_ref,
            component_id=component_id,
            component_version=component_version,
            implementation_id=implementation_id,
            implementation_version=implementation_version,
            parameters=parameters,
            dependency_keys=dependency_keys,
            engine_version=context.engine_version,
            executed_at=context.requested_range.end,
        ),
        validity=ValidityMetadata(
            valid_from_index=valid_from_index,
            valid_to_index=valid_to_index,
        ),
        warmup=WarmUpMetadata(
            warmup_bars=warmup_bars,
            valid_from_index=valid_from_index,
            valid_to_index=valid_to_index,
        ),
        availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
        diagnostics={},
    )


def dependency_results_values(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    output_id: OutputId,
) -> np.ndarray:
    if len(dependency_results) != 1:
        msg = "expected exactly one dependency result"
        raise ValueError(msg)
    result = next(iter(dependency_results.values()))
    series = result.outputs[output_id]
    return np.asarray(series.values, dtype=np.float64)
