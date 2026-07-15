"""Read-only comparison across persisted robustness experiments."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from trading_framework.application.strategy_research.summarize import summarize_strategy_run
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import (
    ExperimentConfigStatus,
    RobustnessExperimentRepository,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)


class RobustnessResearchError(ValidationError):
    """Raised when robustness experiment comparison fails."""


@dataclass(frozen=True, slots=True)
class CompareRobustnessExperimentsRequest:
    """Input for read-only comparison of multiple experiments."""

    experiment_ids: tuple[str, ...]
    storage_root: Path


@dataclass(frozen=True, slots=True)
class RobustnessExperimentComparisonRow:
    """Summary metrics for one experiment."""

    experiment_id: str
    total_configs: int
    completed_configs: int
    failed_configs: int
    best_net_pnl: Decimal | None
    best_strategy_run_id: str | None


@dataclass(frozen=True, slots=True)
class CompareRobustnessExperimentsResult:
    """Comparison table across experiments."""

    rows: tuple[RobustnessExperimentComparisonRow, ...]


def compare_robustness_experiments(
    request: CompareRobustnessExperimentsRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> CompareRobustnessExperimentsResult:
    """Summarize completion state and best net PnL per experiment."""
    if not request.experiment_ids:
        msg = "at least one experiment_id is required"
        raise RobustnessResearchError(msg)

    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)

    rows: list[RobustnessExperimentComparisonRow] = []
    for experiment_id in request.experiment_ids:
        registry = experiment_repo.read_registry(experiment_id)
        completed = [
            entry
            for entry in registry.entries
            if entry.status is ExperimentConfigStatus.COMPLETED and entry.strategy_run_id
        ]
        failed = [
            entry for entry in registry.entries if entry.status is ExperimentConfigStatus.FAILED
        ]
        best_net_pnl: Decimal | None = None
        best_run_id: str | None = None
        for entry in completed:
            assert entry.strategy_run_id is not None
            envelope = strategy_repo.read(StrategyResearchRunRef(run_id=entry.strategy_run_id))
            summary = summarize_strategy_run(
                trades=envelope.trades,
                equity=envelope.equity,
            )
            if best_net_pnl is None or summary.net_pnl > best_net_pnl:
                best_net_pnl = summary.net_pnl
                best_run_id = entry.strategy_run_id
        rows.append(
            RobustnessExperimentComparisonRow(
                experiment_id=experiment_id,
                total_configs=len(registry.entries),
                completed_configs=len(completed),
                failed_configs=len(failed),
                best_net_pnl=best_net_pnl,
                best_strategy_run_id=best_run_id,
            )
        )
    return CompareRobustnessExperimentsResult(rows=tuple(rows))
