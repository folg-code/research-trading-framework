"""Resolve model operand references to AnalysisFrame column keys."""

from typing import assert_never

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression.errors import ModelExpressionError
from trading_framework.model_expression.expressions import OperandReference
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketFieldReference,
)


class FrameColumnResolver:
    """Map operand references to keys present on an assembled AnalysisFrame."""

    def resolve(self, reference: OperandReference, frame: AnalysisFrame) -> str:
        if isinstance(reference, MarketFieldReference):
            key = reference.frame_column_key()
            if key not in frame.columns:
                msg = f"market field column not present on frame: {key!r}"
                raise ModelExpressionError(msg)
            return key

        if isinstance(reference, ComponentOutputReference):
            if reference.alias is not None:
                if reference.alias not in frame.columns:
                    msg = f"aliased component column not present on frame: {reference.alias!r}"
                    raise ModelExpressionError(msg)
                return reference.alias

            for alias, output_ref in frame.column_lineage.items():
                identity = output_ref.computation_identity
                if output_ref.output_id != reference.output_id:
                    continue
                if identity.component_id != reference.component_id:
                    continue
                if identity.parameters != reference.parameters:
                    continue
                if reference.computation_timeframe is not None and (
                    identity.computation_timeframe != reference.computation_timeframe
                ):
                    continue
                return alias

            msg = (
                f"unable to resolve component output column for "
                f"{reference.component_id!s}:{reference.output_id!s}"
            )
            raise ModelExpressionError(msg)

        assert_never(reference)
