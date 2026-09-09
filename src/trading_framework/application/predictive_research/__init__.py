"""Application orchestration for Predictive Research datasets and runs."""

from trading_framework.application.predictive_research.analyze_predictive_run import (
    AnalyzePredictiveRunError,
    AnalyzePredictiveRunRequest,
    AnalyzePredictiveRunResult,
    analyze_predictive_run,
)
from trading_framework.application.predictive_research.analyze_threshold_sensitivity import (
    AnalyzeThresholdSensitivityRequest,
    AnalyzeThresholdSensitivityResult,
    ThresholdSensitivityError,
    analyze_threshold_sensitivity,
)
from trading_framework.application.predictive_research.build_predictive_dataset import (
    BuildPredictiveDatasetRequest,
    BuildPredictiveDatasetResult,
    PredictiveDatasetError,
    build_predictive_dataset,
)
from trading_framework.application.predictive_research.compare_predictive_runs import (
    ComparePredictiveRunsRequest,
    ComparePredictiveRunsResult,
    compare_predictive_runs,
)
from trading_framework.application.predictive_research.evaluate_run_verdict import (
    EvaluateRunVerdictError,
    EvaluateRunVerdictRequest,
    EvaluateRunVerdictResult,
    evaluate_run_verdict,
)
from trading_framework.application.predictive_research.promote_predictive_run import (
    PromotePredictiveRunError,
    PromotePredictiveRunRequest,
    PromotePredictiveRunResult,
    promote_predictive_run,
)
from trading_framework.application.predictive_research.render_report import (
    RenderPredictiveReportError,
    RenderPredictiveReportRequest,
    RenderPredictiveReportResult,
    render_predictive_research_report,
)
from trading_framework.application.predictive_research.resolve_signal_occurrences import (
    ResolvedSignalOccurrenceSample,
    SignalOccurrenceResolutionError,
    resolve_signal_occurrences_sample,
)
from trading_framework.application.predictive_research.run_predictive_research import (
    PredictiveRunError,
    RunPredictiveResearchRequest,
    RunPredictiveResearchResult,
    run_predictive_research,
)

__all__ = [
    "AnalyzePredictiveRunError",
    "AnalyzePredictiveRunRequest",
    "AnalyzePredictiveRunResult",
    "AnalyzeThresholdSensitivityRequest",
    "AnalyzeThresholdSensitivityResult",
    "BuildPredictiveDatasetRequest",
    "BuildPredictiveDatasetResult",
    "ComparePredictiveRunsRequest",
    "ComparePredictiveRunsResult",
    "EvaluateRunVerdictError",
    "EvaluateRunVerdictRequest",
    "EvaluateRunVerdictResult",
    "PredictiveDatasetError",
    "PredictiveRunError",
    "PromotePredictiveRunError",
    "PromotePredictiveRunRequest",
    "PromotePredictiveRunResult",
    "RenderPredictiveReportError",
    "RenderPredictiveReportRequest",
    "RenderPredictiveReportResult",
    "ResolvedSignalOccurrenceSample",
    "RunPredictiveResearchRequest",
    "RunPredictiveResearchResult",
    "SignalOccurrenceResolutionError",
    "ThresholdSensitivityError",
    "analyze_predictive_run",
    "analyze_threshold_sensitivity",
    "build_predictive_dataset",
    "compare_predictive_runs",
    "evaluate_run_verdict",
    "promote_predictive_run",
    "render_predictive_research_report",
    "resolve_signal_occurrences_sample",
    "run_predictive_research",
]
