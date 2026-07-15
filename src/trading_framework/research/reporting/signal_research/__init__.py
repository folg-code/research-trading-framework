"""Signal Research HTML reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.research.reporting.signal_research.contracts import (
    SignalResearchReportSource,
)
from trading_framework.research.reporting.signal_research.report_html import (
    render_signal_research_report_html,
)
from trading_framework.research.reporting.signal_research.view_models import (
    SignalResearchReportViewModel,
    build_signal_research_report_view_model,
)


@dataclass(frozen=True, slots=True)
class SignalResearchReportRef:
    """Reference to one rendered Signal Research HTML report."""

    output_path: Path
    source_run_id: str


def build_signal_research_report(
    analytics: SignalResearchReportSource,
    output_path: Path,
) -> SignalResearchReportRef:
    """Build the Wave 3 HTML dashboard from a finished analytics result."""
    view_model = build_signal_research_report_view_model(analytics)
    render_signal_research_report_html(view_model, output_path)
    return SignalResearchReportRef(
        output_path=output_path,
        source_run_id=analytics.source_run_id,
    )


__all__ = [
    "SignalResearchReportRef",
    "SignalResearchReportViewModel",
    "build_signal_research_report",
    "build_signal_research_report_view_model",
    "render_signal_research_report_html",
]
