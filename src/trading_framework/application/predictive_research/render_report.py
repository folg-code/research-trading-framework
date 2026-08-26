"""Render a Predictive Research HTML report from persisted envelopes."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_importance_path,
    predictive_research_run_leaderboard_path,
    predictive_research_run_metrics_path,
    predictive_research_run_report_path,
    predictive_research_run_selection_path,
)
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.importance import ImportanceTrace
from trading_framework.research.predictive.leaderboard import PredictiveLeaderboard
from trading_framework.research.predictive.metrics import PredictiveMetricsReport
from trading_framework.research.predictive.selection import SelectionTrace
from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.research.reporting.predictive.report_html import (
    render_predictive_research_report_html,
)
from trading_framework.research.reporting.predictive.view_models import (
    build_predictive_report_view_model,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


class RenderPredictiveReportError(ValidationError):
    """Raised when Predictive Research HTML rendering fails."""


@dataclass(frozen=True, slots=True)
class RenderPredictiveReportRequest:
    """Input for read-only HTML rendering of one persisted run."""

    run_ref: PredictiveRunRef
    storage_root: Path
    output_path: Path | None = None
    persist_to_run_dir: bool = True
    clock: Clock | None = None
    run_repository: PredictiveRunRepository | None = None
    dataset_repository: PredictiveDatasetRepository | None = None


@dataclass(frozen=True, slots=True)
class RenderPredictiveReportResult:
    """Outcome of Predictive Research HTML report rendering."""

    run_id: str
    output_path: Path


def render_predictive_research_report(
    request: RenderPredictiveReportRequest,
) -> RenderPredictiveReportResult:
    """Load persisted envelopes and write a standalone HTML report.

    Reads run + dataset + ``metrics.json`` plus optional ``importance.json``,
    ``selection.json``, and ``leaderboard.json``. Never fits, predicts, or
    rebuilds. Never deserializes ``models/fold_*.bin``.
    """
    run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
    dataset_repository = request.dataset_repository or PredictiveDatasetRepository(
        request.storage_root
    )
    run = run_repository.read(request.run_ref)
    dataset = dataset_repository.read(PredictiveDatasetRef(dataset_id=run.manifest.dataset_id))
    metrics_path = predictive_research_run_metrics_path(
        request.storage_root, request.run_ref.run_id
    )
    if not metrics_path.exists():
        msg = f"metrics.json not found: {metrics_path}; run analyze_predictive_run first"
        raise RenderPredictiveReportError(msg)
    metrics = PredictiveMetricsReport.from_dict(
        json.loads(metrics_path.read_text(encoding="utf-8"))
    )
    view = build_predictive_report_view_model(
        PredictiveReportSource(
            run=run,
            dataset=dataset,
            metrics=metrics,
            importance=_optional_sidecar(
                predictive_research_run_importance_path(
                    request.storage_root, request.run_ref.run_id
                ),
                ImportanceTrace.from_dict,
            ),
            selection=_optional_sidecar(
                predictive_research_run_selection_path(
                    request.storage_root, request.run_ref.run_id
                ),
                SelectionTrace.from_dict,
            ),
            leaderboard=_optional_sidecar(
                predictive_research_run_leaderboard_path(
                    request.storage_root, request.run_ref.run_id
                ),
                PredictiveLeaderboard.from_dict,
            ),
        ),
        clock=request.clock or SystemClock(),
    )
    output_path = request.output_path
    if output_path is None:
        if not request.persist_to_run_dir:
            msg = "output_path is required when persist_to_run_dir is false"
            raise RenderPredictiveReportError(msg)
        output_path = predictive_research_run_report_path(
            request.storage_root, request.run_ref.run_id
        )
    written = render_predictive_research_report_html(view, output_path)
    return RenderPredictiveReportResult(run_id=run.manifest.run_id, output_path=written)


def _optional_sidecar[T](path: Path, loader: Callable[[Mapping[str, Any]], T]) -> T | None:
    """Load an optional JSON sidecar; missing files skip the matching panel."""
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON in {path}"
        raise RenderPredictiveReportError(msg) from exc
    if not isinstance(payload, Mapping):
        msg = f"{path.name} must be a JSON object"
        raise RenderPredictiveReportError(msg)
    try:
        return loader(payload)
    except PredictiveSpecError as exc:
        msg = f"invalid sidecar {path.name}: {exc}"
        raise RenderPredictiveReportError(msg) from exc
