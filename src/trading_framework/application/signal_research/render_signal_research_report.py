"""Render Signal Research HTML dashboard from analytics results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchRequest,
    AnalyzeSignalResearchResult,
    analyze_signal_research_run,
)
from trading_framework.application.signal_research.map_definition import (
    map_definition_to_analyze_request,
    resolve_signal_research_definition,
)
from trading_framework.application.signal_research.persist_analytics import (
    load_signal_research_analytics,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import signal_research_report_path
from trading_framework.research.datasets.signal_research import (
    RunDatasetRef,
    SignalResearchDatasetRepository,
)
from trading_framework.research.reporting.signal_research import build_signal_research_report
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import SignalResearchDefinitionSpec
from trading_framework.research.signal_research.loader import load_signal_research_definition


class RenderSignalResearchReportError(ValidationError):
    """Raised when Signal Research report rendering fails."""


@dataclass(frozen=True, slots=True)
class RenderSignalResearchReportRequest:
    """Input for offline Signal Research HTML report rendering."""

    storage_root: Path
    run_id: str
    output_path: Path | None = None
    definition_path: Path | None = None
    use_cached_analytics: bool = True
    persist_to_run_dir: bool = True


@dataclass(frozen=True, slots=True)
class RenderSignalResearchReportResult:
    """Outcome of Signal Research HTML report rendering."""

    output_path: Path
    source_run_id: str
    used_cached_analytics: bool


def render_signal_research_report(
    request: RenderSignalResearchReportRequest,
    *,
    repository: SignalResearchDatasetRepository | None = None,
) -> RenderSignalResearchReportResult:
    """Analyze or load cached analytics and write the Wave 3 HTML dashboard."""
    repo = repository or SignalResearchDatasetRepository(request.storage_root)
    analytics, used_cached = _resolve_analytics(request, repository=repo)
    output_path = request.output_path
    if output_path is None:
        if request.persist_to_run_dir:
            output_path = signal_research_report_path(request.storage_root, request.run_id)
        else:
            msg = "output_path is required when persist_to_run_dir is false"
            raise RenderSignalResearchReportError(msg)

    report_ref = build_signal_research_report(analytics, output_path)
    return RenderSignalResearchReportResult(
        output_path=report_ref.output_path,
        source_run_id=report_ref.source_run_id,
        used_cached_analytics=used_cached,
    )


def _resolve_analytics(
    request: RenderSignalResearchReportRequest,
    *,
    repository: SignalResearchDatasetRepository,
) -> tuple[AnalyzeSignalResearchResult, bool]:
    if request.use_cached_analytics and repository.has_analytics_summary(request.run_id):
        return (
            load_signal_research_analytics(
                run_id=request.run_id,
                storage_root=request.storage_root,
                repository=repository,
            ),
            True,
        )

    analyze_request = _build_analyze_request(request)
    return analyze_signal_research_run(analyze_request, repository=repository), False


def _build_analyze_request(
    request: RenderSignalResearchReportRequest,
) -> AnalyzeSignalResearchRequest:
    run_ref = RunDatasetRef(run_id=request.run_id)
    if request.definition_path is not None:
        spec = load_signal_research_definition(request.definition_path)
        resolved = resolve_signal_research_definition(spec)
        return map_definition_to_analyze_request(
            resolved,
            run_ref=run_ref,
            storage_root=request.storage_root,
        )

    envelope = SignalResearchDatasetRepository(request.storage_root).read(run_ref)
    scope = envelope.manifest.effective_scope()

    return AnalyzeSignalResearchRequest(
        run_ref=run_ref,
        storage_root=request.storage_root,
        conditional_context=scope is ResearchScope.MARKET_AND_SIGNAL,
    )


def load_definition_spec(path: Path) -> SignalResearchDefinitionSpec:
    """Load a definition file for CLI helpers."""
    return load_signal_research_definition(path)
