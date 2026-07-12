"""Assemble wide consumer views from execution workspace results."""

from datetime import datetime

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.alignment_cache import AlignmentCache
from trading_framework.market_analysis.assembly.frame import (
    AnalysisFrame,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.data.align import align_output_series, needs_alignment
from trading_framework.market_analysis.errors import MarketAnalysisError
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.identity.mtf import AlignmentIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe


class AliasCollisionError(MarketAnalysisError):
    """Raised when two frame columns resolve to the same alias."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(f"analysis frame alias collision: {alias!r}")


def default_alias(identity: ComputationIdentity, output_id: OutputId) -> str:
    """Deterministic short alias from resolved computation identity."""
    base = identity.component_id.value.replace(".", "_")
    params = identity.parameters.to_json_dict()
    suffix_parts: list[str] = []
    if "period" in params:
        suffix_parts.append(str(params["period"]))
    if "threshold" in params:
        threshold = params["threshold"]
        suffix_parts.append(
            str(int(threshold)) if float(threshold).is_integer() else str(threshold)
        )
    suffix = "_".join(suffix_parts)
    if suffix:
        return f"{base}_{output_id.value}_{suffix}"
    return f"{base}_{output_id.value}"


class AnalysisFrameAssembler:
    """Materialize a flat aligned matrix from market view and analysis outputs."""

    def assemble(
        self,
        workspace: AnalysisWorkspace,
        request: AnalysisFrameRequest,
        *,
        evaluation_timeframe: Timeframe | None = None,
        evaluation_range: TimeRange | None = None,
        alignment_policy: AlignmentPolicy = AlignmentPolicy.LAST_CLOSED_BAR,
        alignment_cache: AlignmentCache | None = None,
    ) -> AnalysisFrame:
        timestamps = workspace.market_view.timestamps
        eval_range = evaluation_range or _default_evaluation_range(timestamps)
        cache = alignment_cache if alignment_cache is not None else AlignmentCache()

        columns: dict[str, tuple[float, ...]] = {}
        lineage: dict[str, OutputRef] = {}
        used_aliases: set[str] = set()

        for field in request.market_fields:
            column = workspace.market_view.column(field)
            self._register_column(
                alias=field,
                values=column.values,
                output_ref=None,
                columns=columns,
                lineage=lineage,
                used_aliases=used_aliases,
            )

        for spec in request.analysis_columns:
            result = self._find_result(workspace, spec)
            output_ref = OutputRef(
                computation_identity=result.computation_identity,
                output_id=spec.output_id,
            )
            alias = spec.alias or default_alias(result.computation_identity, spec.output_id)
            series = result.outputs[spec.output_id]
            values = self._resolve_column_values(
                result=result,
                series=series,
                output_id=spec.output_id,
                evaluation_timestamps=timestamps,
                evaluation_timeframe=evaluation_timeframe,
                evaluation_range=eval_range,
                alignment_policy=alignment_policy,
                alignment_cache=cache,
            )
            self._register_column(
                alias=alias,
                values=values,
                output_ref=output_ref,
                columns=columns,
                lineage=lineage,
                used_aliases=used_aliases,
            )

        return AnalysisFrame(
            timestamps=timestamps,
            columns=columns,
            column_lineage=lineage,
            session_metadata=workspace.session_metadata,
        )

    def _resolve_column_values(
        self,
        *,
        result: AnalysisResult,
        series: OutputSeries,
        output_id: OutputId,
        evaluation_timestamps: tuple[datetime, ...],
        evaluation_timeframe: Timeframe | None,
        evaluation_range: TimeRange,
        alignment_policy: AlignmentPolicy,
        alignment_cache: AlignmentCache,
    ) -> tuple[float, ...]:
        computation_timeframe = result.computation_identity.computation_timeframe
        if evaluation_timeframe is None or not needs_alignment(
            computation_timeframe=computation_timeframe,
            evaluation_timeframe=evaluation_timeframe,
        ):
            if len(series.values) != len(evaluation_timestamps):
                msg = "column length must match evaluation grid when alignment is disabled"
                raise ValidationError(msg)
            return series.values

        output_policy = self._alignment_policy_for_output(
            result,
            output_id,
            alignment_policy,
        )
        alignment_identity = AlignmentIdentity(
            component_computation_key=result.computation_identity.canonical_key(),
            output_id=output_id.value,
            evaluation_timeframe=evaluation_timeframe,
            evaluation_range=evaluation_range,
            alignment_policy=output_policy,
        )
        cached = alignment_cache.get(alignment_identity)
        if cached is not None:
            return cached

        aligned = align_output_series(
            series,
            evaluation_timestamps=evaluation_timestamps,
            policy=output_policy,
        )
        alignment_cache.put(alignment_identity, aligned)
        return aligned

    @staticmethod
    def _alignment_policy_for_output(
        result: AnalysisResult,
        output_id: OutputId,
        default_policy: AlignmentPolicy,
    ) -> AlignmentPolicy:
        for field in result.output_schema.outputs:
            if field.output_id == output_id:
                return field.alignment_policy
        return default_policy

    def _find_result(
        self,
        workspace: AnalysisWorkspace,
        spec: AnalysisFrameColumnSpec,
    ) -> AnalysisResult:
        for result in workspace.result_store.results().values():
            identity = result.computation_identity
            if (
                identity.component_id == spec.component_id
                and identity.parameters == spec.parameters
            ):
                return result
        msg = f"analysis result not found for {spec.component_id}"
        raise ValidationError(msg)

    def _register_column(
        self,
        *,
        alias: str,
        values: tuple[float, ...],
        output_ref: OutputRef | None,
        columns: dict[str, tuple[float, ...]],
        lineage: dict[str, OutputRef],
        used_aliases: set[str],
    ) -> None:
        if alias in used_aliases:
            raise AliasCollisionError(alias)
        used_aliases.add(alias)
        columns[alias] = values
        if output_ref is not None:
            lineage[alias] = output_ref


def _default_evaluation_range(timestamps: tuple[datetime, ...]) -> TimeRange:
    if not timestamps:
        msg = "evaluation timestamps must be non-empty"
        raise ValidationError(msg)
    return TimeRange(start=timestamps[0], end=timestamps[-1])
