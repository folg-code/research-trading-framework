"""Walk-forward analytics — train selection, OOS stitching, summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.analytics.parameter_sweep import (
    SweepMetric,
    SweepRunMetrics,
    rank_parameter_sweep,
)
from trading_framework.research.robustness.walk_forward import WalkForwardFold


class WalkForwardAnalyticsError(ValidationError):
    """Raised when walk-forward analytics inputs are invalid."""


@dataclass(frozen=True, slots=True)
class WalkForwardTrainSelection:
    """Best train-window config selected for one fold."""

    fold_id: str
    fold_index: int
    config_id: str
    parameter_overrides: dict[str, str]
    strategy_run_id: str
    selection_metric: SweepMetric
    train_metric_value: Decimal | float | None
    train_net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class WalkForwardFoldEvaluation:
    """Train selection and OOS outcome for one fold."""

    fold: WalkForwardFold
    selection: WalkForwardTrainSelection
    oos_strategy_run_id: str
    oos_summary: StrategyRunSummary


@dataclass(frozen=True, slots=True)
class StitchedOosEquity:
    """Chronologically stitched OOS equity curve across folds."""

    fold_count: int
    point_count: int
    equity: pl.DataFrame
    final_equity: Decimal
    max_drawdown: Decimal

    def to_dict(self) -> dict[str, Any]:
        equity_rows: list[dict[str, Any]] = []
        for row in self.equity.to_dicts():
            observed_at = row["observed_at"]
            equity_rows.append(
                {
                    "observed_at": (
                        observed_at.isoformat()
                        if isinstance(observed_at, datetime)
                        else str(observed_at)
                    ),
                    "equity": row["equity"],
                    "drawdown": row["drawdown"],
                    "open_position_count": row["open_position_count"],
                }
            )
        return {
            "fold_count": self.fold_count,
            "point_count": self.point_count,
            "final_equity": str(self.final_equity),
            "max_drawdown": str(self.max_drawdown),
            "equity_rows": equity_rows,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StitchedOosEquity:
        equity = pl.DataFrame(
            [
                {
                    "observed_at": datetime.fromisoformat(str(row["observed_at"])),
                    "equity": float(row["equity"]),
                    "drawdown": float(row["drawdown"]),
                    "open_position_count": int(row["open_position_count"]),
                }
                for row in payload["equity_rows"]
            ],
            schema={
                "observed_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "equity": pl.Float64(),
                "drawdown": pl.Float64(),
                "open_position_count": pl.Int64(),
            },
        )
        return cls(
            fold_count=int(payload["fold_count"]),
            point_count=int(payload["point_count"]),
            equity=equity,
            final_equity=Decimal(str(payload["final_equity"])),
            max_drawdown=Decimal(str(payload["max_drawdown"])),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardAnalytics:
    """Bundled walk-forward analytics for one experiment."""

    experiment_id: str
    fold_evaluations: tuple[WalkForwardFoldEvaluation, ...]
    stitched_oos_equity: StitchedOosEquity

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "fold_evaluations": [
                _fold_evaluation_to_dict(evaluation) for evaluation in self.fold_evaluations
            ],
            "stitched_oos_equity": self.stitched_oos_equity.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardAnalytics:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            fold_evaluations=tuple(
                _fold_evaluation_from_dict(item) for item in payload["fold_evaluations"]
            ),
            stitched_oos_equity=StitchedOosEquity.from_dict(payload["stitched_oos_equity"]),
        )


def select_best_train_config(
    *,
    fold: WalkForwardFold,
    train_runs: tuple[SweepRunMetrics, ...],
    selection_metric: SweepMetric = SweepMetric.NET_PNL,
) -> WalkForwardTrainSelection:
    """Select the best parameter cell using train-window metrics only."""
    if not train_runs:
        msg = f"fold {fold.fold_id} requires at least one train run"
        raise WalkForwardAnalyticsError(msg)
    rankings = rank_parameter_sweep(
        completed_runs=train_runs,
        ranking_metric=selection_metric,
    )
    best = rankings[0]
    return WalkForwardTrainSelection(
        fold_id=fold.fold_id,
        fold_index=fold.fold_index,
        config_id=best.config_id,
        parameter_overrides=best.parameter_overrides,
        strategy_run_id=best.strategy_run_id,
        selection_metric=selection_metric,
        train_metric_value=best.metric_value,
        train_net_pnl=best.net_pnl,
    )


def stitch_oos_equity_curves(
    *,
    fold_segments: tuple[tuple[int, pl.DataFrame], ...],
) -> StitchedOosEquity:
    """Concatenate OOS equity segments in fold order with continuous equity levels."""
    if not fold_segments:
        msg = "walk-forward stitching requires at least one OOS equity segment"
        raise WalkForwardAnalyticsError(msg)

    ordered = sorted(fold_segments, key=lambda item: item[0])
    stitched_parts: list[pl.DataFrame] = []
    running_equity: float | None = None

    for _, segment in ordered:
        if len(segment) == 0:
            continue
        ordered_segment = segment.sort("observed_at")
        if running_equity is None:
            stitched_parts.append(ordered_segment)
            running_equity = float(ordered_segment.row(-1, named=True)["equity"])
            continue

        first_equity = float(ordered_segment.row(0, named=True)["equity"])
        offset = running_equity - first_equity
        adjusted = ordered_segment.with_columns(
            equity=pl.col("equity") + offset,
            drawdown=pl.lit(0.0),
        )
        stitched_parts.append(adjusted)
        running_equity = float(adjusted.row(-1, named=True)["equity"])

    if not stitched_parts:
        msg = "walk-forward stitching produced no equity points"
        raise WalkForwardAnalyticsError(msg)

    stitched = pl.concat(stitched_parts, how="vertical").sort("observed_at")
    stitched = stitched.with_columns(
        drawdown=pl.col("equity") - pl.col("equity").cum_max(),
    )
    final_equity = Decimal(str(stitched.row(-1, named=True)["equity"]))
    max_drawdown = Decimal(str(stitched["drawdown"].min()))
    return StitchedOosEquity(
        fold_count=len(ordered),
        point_count=len(stitched),
        equity=stitched,
        final_equity=final_equity,
        max_drawdown=max_drawdown,
    )


def build_walk_forward_analytics(
    *,
    experiment_id: str,
    fold_evaluations: tuple[WalkForwardFoldEvaluation, ...],
    oos_equity_by_fold_index: dict[int, pl.DataFrame],
) -> WalkForwardAnalytics:
    """Build fold table and stitched OOS equity from completed fold evaluations."""
    if not fold_evaluations:
        msg = "walk-forward analytics requires at least one fold evaluation"
        raise WalkForwardAnalyticsError(msg)
    segments = tuple(
        (evaluation.fold.fold_index, oos_equity_by_fold_index[evaluation.fold.fold_index])
        for evaluation in sorted(fold_evaluations, key=lambda item: item.fold.fold_index)
    )
    stitched = stitch_oos_equity_curves(fold_segments=segments)
    return WalkForwardAnalytics(
        experiment_id=experiment_id,
        fold_evaluations=fold_evaluations,
        stitched_oos_equity=stitched,
    )


def _fold_evaluation_to_dict(evaluation: WalkForwardFoldEvaluation) -> dict[str, Any]:
    return {
        "fold": evaluation.fold.to_dict(),
        "selection": {
            "fold_id": evaluation.selection.fold_id,
            "fold_index": evaluation.selection.fold_index,
            "config_id": evaluation.selection.config_id,
            "parameter_overrides": evaluation.selection.parameter_overrides,
            "strategy_run_id": evaluation.selection.strategy_run_id,
            "selection_metric": evaluation.selection.selection_metric.value,
            "train_metric_value": _serialize_metric(evaluation.selection.train_metric_value),
            "train_net_pnl": str(evaluation.selection.train_net_pnl),
        },
        "oos_strategy_run_id": evaluation.oos_strategy_run_id,
        "oos_summary": _summary_to_dict(evaluation.oos_summary),
    }


def _fold_evaluation_from_dict(payload: dict[str, Any]) -> WalkForwardFoldEvaluation:
    selection_payload = payload["selection"]
    metric_value = selection_payload.get("train_metric_value")
    selection_metric = SweepMetric(str(selection_payload["selection_metric"]))
    return WalkForwardFoldEvaluation(
        fold=WalkForwardFold.from_dict(payload["fold"]),
        selection=WalkForwardTrainSelection(
            fold_id=str(selection_payload["fold_id"]),
            fold_index=int(selection_payload["fold_index"]),
            config_id=str(selection_payload["config_id"]),
            parameter_overrides={
                str(key): str(value)
                for key, value in selection_payload["parameter_overrides"].items()
            },
            strategy_run_id=str(selection_payload["strategy_run_id"]),
            selection_metric=selection_metric,
            train_metric_value=(
                None
                if metric_value is None
                else Decimal(str(metric_value))
                if selection_metric is not SweepMetric.WIN_RATE
                else float(metric_value)
            ),
            train_net_pnl=Decimal(str(selection_payload["train_net_pnl"])),
        ),
        oos_strategy_run_id=str(payload["oos_strategy_run_id"]),
        oos_summary=_summary_from_dict(payload["oos_summary"]),
    )


def _summary_to_dict(summary: StrategyRunSummary) -> dict[str, Any]:
    return {
        "trade_count": summary.trade_count,
        "win_count": summary.win_count,
        "loss_count": summary.loss_count,
        "win_rate": summary.win_rate,
        "gross_pnl": str(summary.gross_pnl),
        "net_pnl": str(summary.net_pnl),
        "total_commission": str(summary.total_commission),
        "max_drawdown": str(summary.max_drawdown),
        "final_equity": str(summary.final_equity),
    }


def _summary_from_dict(payload: dict[str, Any]) -> StrategyRunSummary:
    return StrategyRunSummary(
        trade_count=int(payload["trade_count"]),
        win_count=int(payload["win_count"]),
        loss_count=int(payload["loss_count"]),
        win_rate=(float(payload["win_rate"]) if payload.get("win_rate") is not None else None),
        gross_pnl=Decimal(str(payload["gross_pnl"])),
        net_pnl=Decimal(str(payload["net_pnl"])),
        total_commission=Decimal(str(payload["total_commission"])),
        max_drawdown=Decimal(str(payload["max_drawdown"])),
        final_equity=Decimal(str(payload["final_equity"])),
    )


def _serialize_metric(metric: Decimal | float | None) -> str | float | None:
    if metric is None:
        return None
    if isinstance(metric, Decimal):
        return str(metric)
    return metric
