"""Read-only walk-forward analytics orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import polars as pl

from trading_framework.application.strategy_research.summarize import summarize_strategy_run
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)
from trading_framework.research.robustness.analytics.parameter_sweep import SweepMetric
from trading_framework.research.robustness.analytics.walk_forward import (
    WalkForwardAnalytics,
    WalkForwardFoldEvaluation,
    WalkForwardTrainSelection,
    build_walk_forward_analytics,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.walk_forward import WalkForwardFoldResult


class AnalyzeWalkForwardError(ValidationError):
    """Raised when walk-forward analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeWalkForwardRequest:
    """Input for read-only walk-forward analytics."""

    experiment_id: str
    storage_root: Path
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeWalkForwardResult:
    """Outcome of walk-forward analytics."""

    analytics: WalkForwardAnalytics


def analyze_walk_forward(
    request: AnalyzeWalkForwardRequest,
    *,
    experiment_repository: RobustnessExperimentRepository | None = None,
    strategy_repository: StrategyResearchDatasetRepository | None = None,
) -> AnalyzeWalkForwardResult:
    """Load completed fold results and build stitched OOS analytics."""
    experiment_repo = experiment_repository or RobustnessExperimentRepository(request.storage_root)
    strategy_repo = strategy_repository or StrategyResearchDatasetRepository(request.storage_root)

    manifest = experiment_repo.read_manifest(request.experiment_id)
    if RobustnessExperimentKind.WALK_FORWARD not in manifest.spec.kinds:
        msg = "experiment does not declare WALK_FORWARD"
        raise AnalyzeWalkForwardError(msg)
    if manifest.spec.walk_forward is None:
        msg = "WALK_FORWARD requires walk_forward spec"
        raise AnalyzeWalkForwardError(msg)

    selection_metric = SweepMetric(manifest.spec.walk_forward.selection_metric)
    results = experiment_repo.read_walk_forward_results(request.experiment_id)
    completed_folds = [
        fold
        for fold in results.folds
        if fold.status == "COMPLETED" and fold.oos_strategy_run_id is not None
    ]
    if not completed_folds:
        msg = "walk-forward analytics requires at least one completed fold"
        raise AnalyzeWalkForwardError(msg)

    fold_evaluations: list[WalkForwardFoldEvaluation] = []
    oos_equity_by_fold_index: dict[int, pl.DataFrame] = {}

    for fold_result in completed_folds:
        evaluation = _fold_result_to_evaluation(
            fold_result,
            selection_metric=selection_metric,
            strategy_repo=strategy_repo,
        )
        fold_evaluations.append(evaluation)
        assert fold_result.oos_strategy_run_id is not None
        oos_envelope = strategy_repo.read(
            StrategyResearchRunRef(run_id=fold_result.oos_strategy_run_id)
        )
        oos_equity_by_fold_index[fold_result.fold.fold_index] = oos_envelope.equity

    analytics = build_walk_forward_analytics(
        experiment_id=request.experiment_id,
        fold_evaluations=tuple(fold_evaluations),
        oos_equity_by_fold_index=oos_equity_by_fold_index,
    )
    if request.persist:
        experiment_repo.write_walk_forward_analytics(analytics)
    return AnalyzeWalkForwardResult(analytics=analytics)


def _fold_result_to_evaluation(
    fold_result: WalkForwardFoldResult,
    *,
    selection_metric: SweepMetric,
    strategy_repo: StrategyResearchDatasetRepository,
) -> WalkForwardFoldEvaluation:
    if (
        fold_result.selected_config_id is None
        or fold_result.selected_parameter_overrides is None
        or fold_result.selected_strategy_run_id is None
        or fold_result.train_net_pnl is None
        or fold_result.oos_strategy_run_id is None
    ):
        msg = f"fold {fold_result.fold.fold_id} is missing completed evaluation fields"
        raise AnalyzeWalkForwardError(msg)

    oos_envelope = strategy_repo.read(
        StrategyResearchRunRef(run_id=fold_result.oos_strategy_run_id)
    )
    oos_summary = summarize_strategy_run(
        trades=oos_envelope.trades,
        equity=oos_envelope.equity,
    )
    selection = WalkForwardTrainSelection(
        fold_id=fold_result.fold.fold_id,
        fold_index=fold_result.fold.fold_index,
        config_id=fold_result.selected_config_id,
        parameter_overrides=fold_result.selected_parameter_overrides,
        strategy_run_id=fold_result.selected_strategy_run_id,
        selection_metric=selection_metric,
        train_metric_value=Decimal(fold_result.train_net_pnl),
        train_net_pnl=Decimal(fold_result.train_net_pnl),
    )
    return WalkForwardFoldEvaluation(
        fold=fold_result.fold,
        selection=selection,
        oos_strategy_run_id=fold_result.oos_strategy_run_id,
        oos_summary=oos_summary,
    )
