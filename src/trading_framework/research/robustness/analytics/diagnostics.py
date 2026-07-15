"""Statistical diagnostics analytics — stability, concentration, IS/OOS degradation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardFoldEvaluation
from trading_framework.research.robustness.diagnostics import (
    StatisticalDiagnosticsSpec,
    TimeBucketMode,
)


class DiagnosticsAnalyticsError(ValidationError):
    """Raised when diagnostics analytics inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TimeBucketMetric:
    """Net PnL and trade count for one temporal bucket."""

    bucket_id: str
    trade_count: int
    net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class TemporalStabilityMetrics:
    """Temporal stability summary across time buckets."""

    bucket_mode: str
    buckets: tuple[TimeBucketMetric, ...]
    bucket_count: int
    net_pnl_range: Decimal
    net_pnl_coefficient_of_variation: Decimal | None


@dataclass(frozen=True, slots=True)
class PnlConcentrationMetrics:
    """Share of total PnL contributed by top trades and days."""

    total_net_pnl: Decimal
    top_k_trades: int
    top_k_days: int
    top_trades_share: Decimal
    top_days_share: Decimal
    top_trade_ids: tuple[str, ...]
    top_session_days: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FoldDegradationRow:
    """Train vs OOS degradation for one walk-forward fold."""

    fold_id: str
    fold_index: int
    train_net_pnl: Decimal
    oos_net_pnl: Decimal
    degradation_delta: Decimal
    degradation_ratio: Decimal | None


@dataclass(frozen=True, slots=True)
class IsOosDegradationMetrics:
    """Aggregated IS/OOS degradation across walk-forward folds."""

    fold_rows: tuple[FoldDegradationRow, ...]
    mean_degradation_delta: Decimal
    oos_beats_train_count: int


@dataclass(frozen=True, slots=True)
class StatisticalDiagnosticsAnalytics:
    """Bundled statistical diagnostics for one experiment."""

    experiment_id: str
    reference_strategy_run_id: str
    temporal_stability: TemporalStabilityMetrics
    pnl_concentration: PnlConcentrationMetrics
    is_oos_degradation: IsOosDegradationMetrics | None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "reference_strategy_run_id": self.reference_strategy_run_id,
            "temporal_stability": _temporal_stability_to_dict(self.temporal_stability),
            "pnl_concentration": _pnl_concentration_to_dict(self.pnl_concentration),
        }
        if self.is_oos_degradation is not None:
            payload["is_oos_degradation"] = _is_oos_degradation_to_dict(self.is_oos_degradation)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StatisticalDiagnosticsAnalytics:
        degradation_payload = payload.get("is_oos_degradation")
        return cls(
            experiment_id=str(payload["experiment_id"]),
            reference_strategy_run_id=str(payload["reference_strategy_run_id"]),
            temporal_stability=_temporal_stability_from_dict(payload["temporal_stability"]),
            pnl_concentration=_pnl_concentration_from_dict(payload["pnl_concentration"]),
            is_oos_degradation=(
                _is_oos_degradation_from_dict(degradation_payload)
                if degradation_payload is not None
                else None
            ),
        )


def build_statistical_diagnostics_analytics(
    *,
    experiment_id: str,
    reference_strategy_run_id: str,
    trades: pl.DataFrame,
    spec: StatisticalDiagnosticsSpec,
    fold_evaluations: tuple[WalkForwardFoldEvaluation, ...] | None = None,
) -> StatisticalDiagnosticsAnalytics:
    """Build temporal stability, concentration, and optional IS/OOS degradation metrics."""
    temporal_stability = compute_temporal_stability(
        trades=trades,
        bucket_mode=spec.time_bucket_mode,
    )
    pnl_concentration = compute_pnl_concentration(
        trades=trades,
        top_k_trades=spec.top_k_trades,
        top_k_days=spec.top_k_days,
    )
    is_oos_degradation = (
        compute_is_oos_degradation(fold_evaluations=fold_evaluations) if fold_evaluations else None
    )
    return StatisticalDiagnosticsAnalytics(
        experiment_id=experiment_id,
        reference_strategy_run_id=reference_strategy_run_id,
        temporal_stability=temporal_stability,
        pnl_concentration=pnl_concentration,
        is_oos_degradation=is_oos_degradation,
    )


def compute_temporal_stability(
    *,
    trades: pl.DataFrame,
    bucket_mode: TimeBucketMode,
) -> TemporalStabilityMetrics:
    """Compute metric drift across month or quarter buckets."""
    if len(trades) == 0:
        return TemporalStabilityMetrics(
            bucket_mode=bucket_mode.value,
            buckets=(),
            bucket_count=0,
            net_pnl_range=Decimal("0"),
            net_pnl_coefficient_of_variation=None,
        )

    bucket_expr = (
        pl.col("exit_fill_at").dt.strftime("%Y-%m")
        if bucket_mode is TimeBucketMode.MONTH
        else (
            pl.col("exit_fill_at").dt.year().cast(pl.Utf8)
            + "-Q"
            + ((pl.col("exit_fill_at").dt.month() - 1) // 3 + 1).cast(pl.Utf8)
        )
    )
    bucketed = trades.with_columns(bucket_id=bucket_expr)
    aggregated = (
        bucketed.group_by("bucket_id")
        .agg(
            pl.len().alias("trade_count"),
            pl.col("net_pnl").sum().alias("net_pnl"),
        )
        .sort("bucket_id")
    )

    buckets = tuple(
        TimeBucketMetric(
            bucket_id=str(row["bucket_id"]),
            trade_count=int(row["trade_count"]),
            net_pnl=Decimal(str(row["net_pnl"])),
        )
        for row in aggregated.iter_rows(named=True)
    )
    net_pnls = [bucket.net_pnl for bucket in buckets]
    net_pnl_range = max(net_pnls) - min(net_pnls) if net_pnls else Decimal("0")
    coefficient = _coefficient_of_variation(net_pnls)
    return TemporalStabilityMetrics(
        bucket_mode=bucket_mode.value,
        buckets=buckets,
        bucket_count=len(buckets),
        net_pnl_range=net_pnl_range,
        net_pnl_coefficient_of_variation=coefficient,
    )


def compute_pnl_concentration(
    *,
    trades: pl.DataFrame,
    top_k_trades: int,
    top_k_days: int,
) -> PnlConcentrationMetrics:
    """Compute share of total PnL from top trades and session days."""
    if len(trades) == 0:
        return PnlConcentrationMetrics(
            total_net_pnl=Decimal("0"),
            top_k_trades=top_k_trades,
            top_k_days=top_k_days,
            top_trades_share=Decimal("0"),
            top_days_share=Decimal("0"),
            top_trade_ids=(),
            top_session_days=(),
        )

    total_net_pnl = _sum_decimal(trades, "net_pnl")
    top_trades = trades.sort("net_pnl", descending=True).head(top_k_trades)
    top_trade_ids = tuple(str(value) for value in top_trades.get_column("trade_id").to_list())
    top_trades_pnl = _sum_decimal(top_trades, "net_pnl")

    trades_with_day = trades.with_columns(
        session_day=pl.col("exit_fill_at").dt.date().cast(pl.Utf8)
    )
    day_pnl = trades_with_day.group_by("session_day").agg(pl.col("net_pnl").sum().alias("day_pnl"))
    top_days_frame = day_pnl.sort("day_pnl", descending=True).head(top_k_days)
    top_session_days = tuple(
        str(value) for value in top_days_frame.get_column("session_day").to_list()
    )
    top_days_pnl = _sum_decimal(top_days_frame, "day_pnl")

    return PnlConcentrationMetrics(
        total_net_pnl=total_net_pnl,
        top_k_trades=top_k_trades,
        top_k_days=top_k_days,
        top_trades_share=_share(top_trades_pnl, total_net_pnl),
        top_days_share=_share(top_days_pnl, total_net_pnl),
        top_trade_ids=top_trade_ids,
        top_session_days=top_session_days,
    )


def compute_is_oos_degradation(
    *,
    fold_evaluations: tuple[WalkForwardFoldEvaluation, ...],
) -> IsOosDegradationMetrics:
    """Compute train vs OOS degradation from walk-forward fold evaluations."""
    if not fold_evaluations:
        msg = "IS/OOS degradation requires at least one fold evaluation"
        raise DiagnosticsAnalyticsError(msg)

    rows: list[FoldDegradationRow] = []
    for evaluation in sorted(fold_evaluations, key=lambda item: item.fold.fold_index):
        train_net_pnl = evaluation.selection.train_net_pnl
        oos_net_pnl = evaluation.oos_summary.net_pnl
        degradation_delta = oos_net_pnl - train_net_pnl
        degradation_ratio = oos_net_pnl / train_net_pnl if train_net_pnl != 0 else None
        rows.append(
            FoldDegradationRow(
                fold_id=evaluation.fold.fold_id,
                fold_index=evaluation.fold.fold_index,
                train_net_pnl=train_net_pnl,
                oos_net_pnl=oos_net_pnl,
                degradation_delta=degradation_delta,
                degradation_ratio=degradation_ratio,
            )
        )

    deltas = [row.degradation_delta for row in rows]
    return IsOosDegradationMetrics(
        fold_rows=tuple(rows),
        mean_degradation_delta=_mean_decimal(deltas),
        oos_beats_train_count=sum(1 for row in rows if row.oos_net_pnl > row.train_net_pnl),
    )


def _sum_decimal(frame: pl.DataFrame, column: str) -> Decimal:
    if len(frame) == 0:
        return Decimal("0")
    return Decimal(str(frame.get_column(column).sum()))


def _share(part: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    return part / total


def _mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def _coefficient_of_variation(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    mean_value = _mean_decimal(values)
    if mean_value == 0:
        return None
    variance = sum((value - mean_value) ** 2 for value in values) / Decimal(len(values))
    if variance == 0:
        return Decimal("0")
    return Decimal(str(math.sqrt(float(variance)))) / abs(mean_value)


def _temporal_stability_to_dict(metrics: TemporalStabilityMetrics) -> dict[str, Any]:
    return {
        "bucket_mode": metrics.bucket_mode,
        "bucket_count": metrics.bucket_count,
        "net_pnl_range": str(metrics.net_pnl_range),
        "net_pnl_coefficient_of_variation": (
            str(metrics.net_pnl_coefficient_of_variation)
            if metrics.net_pnl_coefficient_of_variation is not None
            else None
        ),
        "buckets": [
            {
                "bucket_id": bucket.bucket_id,
                "trade_count": bucket.trade_count,
                "net_pnl": str(bucket.net_pnl),
            }
            for bucket in metrics.buckets
        ],
    }


def _temporal_stability_from_dict(payload: dict[str, Any]) -> TemporalStabilityMetrics:
    coefficient = payload.get("net_pnl_coefficient_of_variation")
    return TemporalStabilityMetrics(
        bucket_mode=str(payload["bucket_mode"]),
        buckets=tuple(
            TimeBucketMetric(
                bucket_id=str(bucket["bucket_id"]),
                trade_count=int(bucket["trade_count"]),
                net_pnl=Decimal(str(bucket["net_pnl"])),
            )
            for bucket in payload["buckets"]
        ),
        bucket_count=int(payload["bucket_count"]),
        net_pnl_range=Decimal(str(payload["net_pnl_range"])),
        net_pnl_coefficient_of_variation=(
            Decimal(str(coefficient)) if coefficient is not None else None
        ),
    )


def _pnl_concentration_to_dict(metrics: PnlConcentrationMetrics) -> dict[str, Any]:
    return {
        "total_net_pnl": str(metrics.total_net_pnl),
        "top_k_trades": metrics.top_k_trades,
        "top_k_days": metrics.top_k_days,
        "top_trades_share": str(metrics.top_trades_share),
        "top_days_share": str(metrics.top_days_share),
        "top_trade_ids": list(metrics.top_trade_ids),
        "top_session_days": list(metrics.top_session_days),
    }


def _pnl_concentration_from_dict(payload: dict[str, Any]) -> PnlConcentrationMetrics:
    return PnlConcentrationMetrics(
        total_net_pnl=Decimal(str(payload["total_net_pnl"])),
        top_k_trades=int(payload["top_k_trades"]),
        top_k_days=int(payload["top_k_days"]),
        top_trades_share=Decimal(str(payload["top_trades_share"])),
        top_days_share=Decimal(str(payload["top_days_share"])),
        top_trade_ids=tuple(str(value) for value in payload["top_trade_ids"]),
        top_session_days=tuple(str(value) for value in payload["top_session_days"]),
    )


def _is_oos_degradation_to_dict(metrics: IsOosDegradationMetrics) -> dict[str, Any]:
    return {
        "mean_degradation_delta": str(metrics.mean_degradation_delta),
        "oos_beats_train_count": metrics.oos_beats_train_count,
        "fold_rows": [
            {
                "fold_id": row.fold_id,
                "fold_index": row.fold_index,
                "train_net_pnl": str(row.train_net_pnl),
                "oos_net_pnl": str(row.oos_net_pnl),
                "degradation_delta": str(row.degradation_delta),
                "degradation_ratio": (
                    str(row.degradation_ratio) if row.degradation_ratio is not None else None
                ),
            }
            for row in metrics.fold_rows
        ],
    }


def _is_oos_degradation_from_dict(payload: dict[str, Any]) -> IsOosDegradationMetrics:
    return IsOosDegradationMetrics(
        fold_rows=tuple(
            FoldDegradationRow(
                fold_id=str(row["fold_id"]),
                fold_index=int(row["fold_index"]),
                train_net_pnl=Decimal(str(row["train_net_pnl"])),
                oos_net_pnl=Decimal(str(row["oos_net_pnl"])),
                degradation_delta=Decimal(str(row["degradation_delta"])),
                degradation_ratio=(
                    Decimal(str(row["degradation_ratio"]))
                    if row.get("degradation_ratio") is not None
                    else None
                ),
            )
            for row in payload["fold_rows"]
        ),
        mean_degradation_delta=Decimal(str(payload["mean_degradation_delta"])),
        oos_beats_train_count=int(payload["oos_beats_train_count"]),
    )
