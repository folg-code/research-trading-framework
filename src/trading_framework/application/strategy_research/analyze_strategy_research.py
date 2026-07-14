"""Analyze one persisted Strategy Research run — read-only summary orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.strategy_research.summarize import (
    StrategyRunSummary,
    summarize_strategy_run,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)


class AnalyzeStrategyResearchError(ValidationError):
    """Raised when Strategy Research analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeStrategyResearchRequest:
    """Input for read-only analytics over one persisted Strategy Research run."""

    run_ref: StrategyResearchRunRef
    storage_root: Path


@dataclass(frozen=True, slots=True)
class AnalyzeStrategyResearchResult:
    """Ephemeral analytics result for one persisted Strategy Research run."""

    source_run_id: str
    summary: StrategyRunSummary


def analyze_strategy_research_run(
    request: AnalyzeStrategyResearchRequest,
    *,
    repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeStrategyResearchResult:
    """Load one persisted run and return read-only summary metrics."""
    repo = repository or StrategyResearchDatasetRepository(request.storage_root)
    envelope = repo.read(request.run_ref)
    summary = summarize_strategy_run(trades=envelope.trades, equity=envelope.equity)
    return AnalyzeStrategyResearchResult(
        source_run_id=envelope.manifest.run_id,
        summary=summary,
    )
