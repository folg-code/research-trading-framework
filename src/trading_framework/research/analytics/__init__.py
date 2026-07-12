"""Signal Research analytics — read-only interpretation of persisted runs."""

from trading_framework.research.analytics.aggregates import (
    SummarizeAnalysisFrameResult,
    compute_run_summary,
    summarize_analysis_frame,
    summarize_run_summaries,
)
from trading_framework.research.analytics.dimensions import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.analytics.metadata import (
    CME_ES_TIME_OF_DAY_TIMEZONE,
    DEFAULT_TIME_OF_DAY_BUCKET_MINUTES,
    AnalyticsResultMetadata,
)
from trading_framework.research.analytics.schemas import (
    empty_analysis_frame,
    empty_run_summaries,
    validate_analysis_frame,
    validate_run_summaries,
)

__all__ = [
    "CME_ES_TIME_OF_DAY_TIMEZONE",
    "DEFAULT_TIME_OF_DAY_BUCKET_MINUTES",
    "ENTITY_KIND_OBSERVATION",
    "ENTITY_KIND_SIGNAL",
    "AnalyticsResultMetadata",
    "AnalyticsTimestampBasis",
    "GroupDimension",
    "OutcomeAnalyticsFilter",
    "SummarizeAnalysisFrameResult",
    "build_analysis_frame",
    "compute_run_summary",
    "empty_analysis_frame",
    "empty_run_summaries",
    "summarize_analysis_frame",
    "summarize_run_summaries",
    "validate_analysis_frame",
    "validate_run_summaries",
]
