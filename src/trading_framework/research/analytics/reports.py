"""Backward-compatible entrypoint for Signal Research HTML reports."""

from __future__ import annotations

from pathlib import Path

from trading_framework.research.reporting.signal_research.contracts import (
    SignalResearchReportSource,
)
from trading_framework.research.reporting.signal_research.report_html import (
    render_signal_research_report_html,
)
from trading_framework.research.reporting.signal_research.view_models import (
    build_signal_research_report_view_model,
)

AnalyticsReportSource = SignalResearchReportSource


def render_signal_research_report(
    result: SignalResearchReportSource,
    output_path: Path,
) -> Path:
    """Render the Wave 3 HTML dashboard from a finished analytics result.

    Presentation-only: consumes ``AnalyzeSignalResearchResult`` or any object
    implementing ``SignalResearchReportSource`` — no Parquet reads, joins or
    aggregate recomputation.
    """
    view_model = build_signal_research_report_view_model(result)
    return render_signal_research_report_html(view_model, output_path)


__all__ = ["AnalyticsReportSource", "render_signal_research_report"]
