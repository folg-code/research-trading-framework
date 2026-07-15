"""Persist and load cached Signal Research analytics sidecars."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.signal_research.analytics_envelope import (
    signal_research_analytics_from_dict,
    signal_research_analytics_to_dict,
)
from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.signal_research import SignalResearchDatasetRepository


class PersistSignalResearchAnalyticsError(ValidationError):
    """Raised when analytics sidecar persistence fails."""


@dataclass(frozen=True, slots=True)
class PersistSignalResearchAnalyticsResult:
    """Outcome of analytics sidecar persistence."""

    summary_path: Path


def persist_signal_research_analytics(
    analytics: AnalyzeSignalResearchResult,
    *,
    storage_root: Path,
    repository: SignalResearchDatasetRepository | None = None,
) -> PersistSignalResearchAnalyticsResult:
    """Write one analytics result to ``analytics/summary.json`` for the run."""
    repo = repository or SignalResearchDatasetRepository(storage_root)
    payload = signal_research_analytics_to_dict(analytics)
    summary_path = repo.write_analytics_summary(analytics.source_run_id, payload)
    return PersistSignalResearchAnalyticsResult(summary_path=summary_path)


def load_signal_research_analytics(
    *,
    run_id: str,
    storage_root: Path,
    repository: SignalResearchDatasetRepository | None = None,
) -> AnalyzeSignalResearchResult:
    """Load one cached analytics result without recomputing aggregates."""
    repo = repository or SignalResearchDatasetRepository(storage_root)
    payload = repo.read_analytics_summary_payload(run_id)
    analytics = signal_research_analytics_from_dict(payload)
    if analytics.source_run_id != run_id:
        msg = "cached analytics source_run_id does not match requested run_id"
        raise PersistSignalResearchAnalyticsError(msg)
    return analytics
