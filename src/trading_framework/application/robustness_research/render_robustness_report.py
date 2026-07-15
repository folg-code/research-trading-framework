"""Render robustness experiment HTML dashboard from persisted report view model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.robustness.report_html import render_robustness_report


class RenderRobustnessReportError(ValidationError):
    """Raised when robustness report rendering fails."""


@dataclass(frozen=True, slots=True)
class RenderRobustnessReportRequest:
    """Input for offline robustness HTML report rendering."""

    experiment_id: str
    storage_root: Path
    output_path: Path | None = None
    persist_to_experiment_dir: bool = True


@dataclass(frozen=True, slots=True)
class RenderRobustnessReportResult:
    """Outcome of robustness HTML report rendering."""

    output_path: Path


def render_robustness_experiment_report(
    request: RenderRobustnessReportRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
) -> RenderRobustnessReportResult:
    """Load report view model and write standalone HTML dashboard."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    view_model = experiment_repo.read_report_view_model(request.experiment_id)
    if request.output_path is not None:
        output_path = render_robustness_report(view_model, request.output_path)
    elif request.persist_to_experiment_dir:
        from trading_framework.infrastructure.storage.paths import robustness_experiment_report_dir

        default_path = (
            robustness_experiment_report_dir(request.storage_root, request.experiment_id)
            / "robustness_report.html"
        )
        output_path = render_robustness_report(view_model, default_path)
    else:
        msg = "output_path is required when persist_to_experiment_dir is false"
        raise RenderRobustnessReportError(msg)
    return RenderRobustnessReportResult(output_path=output_path)
