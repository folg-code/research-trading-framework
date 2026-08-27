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
    build_calibration_figure,
    build_discrimination_figure,
    build_feature_importance_figure,
    build_fold_timeline_figure,
    build_leaderboard_figure,
    build_learning_curves_figure,
    build_metric_stability_figure,
    build_model_vs_baselines_figure,
    build_panel_figure,
    build_prediction_buckets_figure,
    build_prediction_quality_figure,
    build_sample_composition_figure,
    build_selection_trace_figure,
    build_window_accounting_figure,
    require_plotly,
)
from trading_framework.research.reporting.predictive.quality import (
    PredictiveQualityFlag,
    PredictiveQualityWarning,
    PredictiveReportQualityRules,
    evaluate_predictive_quality_flags,
    primary_metric_name,
)
from trading_framework.research.reporting.predictive.report_html import (
    PANEL_BODY_RENDERERS,
    render_predictive_research_report_html,
)
from trading_framework.research.reporting.predictive.view_models import (
    FoldMetricSnapshot,
    FoldTimelineBand,
    PredictiveReportViewModel,
    build_predictive_report_view_model,
)

__all__ = [
    "PANEL_BODY_RENDERERS",
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
    "build_calibration_figure",
    "build_discrimination_figure",
    "build_feature_importance_figure",
    "build_fold_timeline_figure",
    "build_leaderboard_figure",
    "build_learning_curves_figure",
    "build_metric_stability_figure",
    "build_model_vs_baselines_figure",
    "build_panel_figure",
    "build_prediction_buckets_figure",
    "build_prediction_quality_figure",
    "build_predictive_report_view_model",
    "build_sample_composition_figure",
    "build_selection_trace_figure",
    "build_window_accounting_figure",
    "evaluate_predictive_quality_flags",
    "format_count",
    "format_metric",
    "format_return",
    "format_share",
    "primary_metric_name",
    "render_predictive_research_report_html",
    "require_plotly",
    "resolve_report_panels",
]
