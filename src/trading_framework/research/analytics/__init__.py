"""Signal Research analytics — read-only interpretation of persisted runs."""

from trading_framework.research.analytics.aggregates import (
    compute_run_summary,
    summarize_run_summaries,
)
from trading_framework.research.analytics.conditional import (
    compute_conditional_comparison,
    summarize_conditional_comparison,
)
from trading_framework.research.analytics.dimensions import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.analytics.grouping import (
    compute_grouped_summary,
    summarize_grouped_summaries,
)
from trading_framework.research.analytics.metadata import (
    CME_ES_TIME_OF_DAY_TIMEZONE,
    DEFAULT_TIME_OF_DAY_BUCKET_MINUTES,
    AnalyticsResultMetadata,
)
from trading_framework.research.analytics.metrics import aggregate_complete_metrics
from trading_framework.research.analytics.reports import (
    AnalyticsReportSource,
    render_signal_research_report,
)
from trading_framework.research.analytics.schemas import (
    empty_analysis_frame,
    empty_conditional_comparison,
    empty_grouped_summaries,
    empty_run_summaries,
    validate_analysis_frame,
    validate_conditional_comparison,
    validate_grouped_summaries,
    validate_run_summaries,
)
from trading_framework.research.analytics.summarize import (
    SummarizeAnalysisFrameResult,
    summarize_analysis_frame,
)

__all__ = [
    "CME_ES_TIME_OF_DAY_TIMEZONE",
    "DEFAULT_TIME_OF_DAY_BUCKET_MINUTES",
    "ENTITY_KIND_OBSERVATION",
    "ENTITY_KIND_SIGNAL",
    "AnalyticsReportSource",
    "AnalyticsResultMetadata",
    "AnalyticsTimestampBasis",
    "GroupDimension",
    "OutcomeAnalyticsFilter",
    "SummarizeAnalysisFrameResult",
    "aggregate_complete_metrics",
    "build_analysis_frame",
    "compute_conditional_comparison",
    "compute_grouped_summary",
    "compute_run_summary",
    "empty_analysis_frame",
    "empty_conditional_comparison",
    "empty_grouped_summaries",
    "empty_run_summaries",
    "render_signal_research_report",
    "summarize_analysis_frame",
    "summarize_conditional_comparison",
    "summarize_grouped_summaries",
    "summarize_run_summaries",
    "validate_analysis_frame",
    "validate_conditional_comparison",
    "validate_grouped_summaries",
    "validate_run_summaries",
]
