"""Predictive Research HTML reporting."""

from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.research.reporting.predictive.formatting import (
    format_count,
    format_metric,
    format_return,
    format_share,
)
from trading_framework.research.reporting.predictive.panels import (
    PREDICTIVE_REPORT_PANELS,
    RESERVED_PANEL_IDS,
    PanelStatus,
    ResolvedPanel,
    resolve_report_panels,
)
from trading_framework.research.reporting.predictive.plotly_figures import (
    build_fold_timeline_figure,
    build_metric_stability_figure,
    build_model_vs_baselines_figure,
    build_sample_composition_figure,
    require_plotly,
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
    "build_fold_timeline_figure",
    "build_metric_stability_figure",
    "build_model_vs_baselines_figure",
    "build_predictive_report_view_model",
    "build_sample_composition_figure",
    "evaluate_predictive_quality_flags",
    "format_count",
    "format_metric",
    "format_return",
    "format_share",
    "primary_metric_name",
    "require_plotly",
    "resolve_report_panels",
]
