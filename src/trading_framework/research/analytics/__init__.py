"""Signal Research analytics — read-only interpretation of persisted runs."""

from trading_framework.research.analytics.dimensions import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.analytics.schemas import (
    empty_analysis_frame,
    validate_analysis_frame,
)

__all__ = [
    "ENTITY_KIND_OBSERVATION",
    "ENTITY_KIND_SIGNAL",
    "AnalyticsTimestampBasis",
    "GroupDimension",
    "OutcomeAnalyticsFilter",
    "build_analysis_frame",
    "empty_analysis_frame",
    "validate_analysis_frame",
]
