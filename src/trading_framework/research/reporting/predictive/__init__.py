"""Predictive Research HTML reporting."""

from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.research.reporting.predictive.panels import (
    PREDICTIVE_REPORT_PANELS,
    RESERVED_PANEL_IDS,
    PanelStatus,
    ResolvedPanel,
    resolve_report_panels,
)
from trading_framework.research.reporting.predictive.quality import (
    PredictiveQualityFlag,
    PredictiveQualityWarning,
    PredictiveReportQualityRules,
    evaluate_predictive_quality_flags,
    primary_metric_name,
)
from trading_framework.research.reporting.predictive.view_models import (
    FoldMetricSnapshot,
    FoldTimelineBand,
    PredictiveReportViewModel,
    build_predictive_report_view_model,
)

__all__ = [
    "PREDICTIVE_REPORT_PANELS",
    "RESERVED_PANEL_IDS",
    "FoldMetricSnapshot",
    "FoldTimelineBand",
    "PanelStatus",
    "PredictiveQualityFlag",
    "PredictiveQualityWarning",
    "PredictiveReportQualityRules",
    "PredictiveReportSource",
    "PredictiveReportViewModel",
    "ResolvedPanel",
    "build_predictive_report_view_model",
    "evaluate_predictive_quality_flags",
    "primary_metric_name",
    "resolve_report_panels",
]
