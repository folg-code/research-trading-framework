"""AnalysisFrame consumer view contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters


@dataclass(frozen=True, slots=True)
class AnalysisFrameColumnSpec:
    """One analysis output column to include in a consumer frame."""

    component_id: ComponentId
    parameters: CanonicalParameters
    output_id: OutputId
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisFrameRequest:
    """Request to materialize a wide consumer view from one workspace."""

    market_fields: tuple[str, ...] = ("open", "high", "low", "close", "volume")
    analysis_columns: tuple[AnalysisFrameColumnSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisFrame:
    """Workflow-specific aligned analytical matrix (not a domain aggregate root)."""

    timestamps: tuple[datetime, ...]
    columns: Mapping[str, tuple[float, ...]]
    column_lineage: Mapping[str, OutputRef]
    session_metadata: TradingSessionMetadata | None = None
