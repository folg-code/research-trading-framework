"""Assemble wide consumer views from execution workspace results."""

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import (
    AnalysisFrame,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.errors import MarketAnalysisError
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace


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
    ) -> AnalysisFrame:
        timestamps = workspace.market_view.timestamps
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
            self._register_column(
                alias=alias,
                values=series.values,
                output_ref=output_ref,
                columns=columns,
                lineage=lineage,
                used_aliases=used_aliases,
            )

        return AnalysisFrame(
            timestamps=timestamps,
            columns=columns,
            column_lineage=lineage,
        )

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
