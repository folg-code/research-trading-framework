"""Monte Carlo analytics — trade resampling, envelopes, and tail probabilities."""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.monte_carlo import (
    MonteCarloMethod,
    MonteCarloMethodResult,
    MonteCarloPathSummary,
    MonteCarloPercentilePoint,
    MonteCarloResults,
    MonteCarloSpec,
)


class MonteCarloAnalyticsError(ValidationError):
    """Raised when Monte Carlo analytics inputs are invalid."""


@dataclass(frozen=True, slots=True)
class DistributionSummary:
    """Distribution summary over simulated path terminal metrics."""

    method: str
    path_count: int
    mean_terminal_equity: Decimal
    mean_net_pnl: Decimal
    mean_max_drawdown: Decimal
    p5_terminal_equity: Decimal
    p50_terminal_equity: Decimal
    p95_terminal_equity: Decimal


@dataclass(frozen=True, slots=True)
class TailProbabilityMetrics:
    """Tail probabilities derived from simulated paths."""

    method: str
    probability_terminal_pnl_negative: Decimal
    probability_max_drawdown_exceeds_threshold: Decimal | None


@dataclass(frozen=True, slots=True)
class MonteCarloAnalytics:
    """Bundled Monte Carlo analytics for one experiment."""

    experiment_id: str
    reference_strategy_run_id: str
    rng_seed: int
    distribution_summaries: tuple[DistributionSummary, ...]
    tail_probabilities: tuple[TailProbabilityMetrics, ...]
    method_results: tuple[MonteCarloMethodResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "reference_strategy_run_id": self.reference_strategy_run_id,
            "rng_seed": self.rng_seed,
            "distribution_summaries": [
                _distribution_summary_to_dict(summary) for summary in self.distribution_summaries
            ],
            "tail_probabilities": [
                _tail_probability_to_dict(metrics) for metrics in self.tail_probabilities
            ],
            "method_results": [method.to_dict() for method in self.method_results],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloAnalytics:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            reference_strategy_run_id=str(payload["reference_strategy_run_id"]),
            rng_seed=int(payload["rng_seed"]),
            distribution_summaries=tuple(
                _distribution_summary_from_dict(item) for item in payload["distribution_summaries"]
            ),
            tail_probabilities=tuple(
                _tail_probability_from_dict(item) for item in payload["tail_probabilities"]
            ),
            method_results=tuple(
                MonteCarloMethodResult.from_dict(item) for item in payload["method_results"]
            ),
        )


def run_monte_carlo_simulation(
    *,
    trades: pl.DataFrame,
    spec: MonteCarloSpec,
    initial_capital: Decimal,
) -> tuple[MonteCarloMethodResult, ...]:
    """Simulate trade-level Monte Carlo paths for each declared method."""
    trade_pnls = extract_ordered_trade_pnls(trades)
    blocks = build_session_day_blocks(trades)
    rng = random.Random(spec.rng_seed)
    method_results: list[MonteCarloMethodResult] = []

    for method in spec.methods:
        paths = _simulate_paths_for_method(
            method=method,
            trade_pnls=trade_pnls,
            blocks=blocks,
            path_count=spec.path_count,
            rng=rng,
        )
        path_summaries, percentile_equity = _summarize_paths(
            paths=paths,
            method=method,
            initial_capital=initial_capital,
        )
        method_results.append(
            MonteCarloMethodResult(
                method=method.value,
                path_count=spec.path_count,
                path_summaries=path_summaries,
                percentile_equity=percentile_equity,
            )
        )
    return tuple(method_results)


def build_monte_carlo_analytics(
    *,
    experiment_id: str,
    results: MonteCarloResults,
    max_drawdown_threshold: Decimal | None,
) -> MonteCarloAnalytics:
    """Build distribution summaries and tail probabilities from persisted MC results."""
    distribution_summaries: list[DistributionSummary] = []
    tail_probabilities: list[TailProbabilityMetrics] = []

    for method_result in results.methods:
        distribution_summaries.append(_distribution_summary_from_paths(method_result))
        tail_probabilities.append(
            _tail_probabilities_from_paths(
                method_result=method_result,
                max_drawdown_threshold=max_drawdown_threshold,
            )
        )

    return MonteCarloAnalytics(
        experiment_id=experiment_id,
        reference_strategy_run_id=results.reference_strategy_run_id,
        rng_seed=results.rng_seed,
        distribution_summaries=tuple(distribution_summaries),
        tail_probabilities=tuple(tail_probabilities),
        method_results=results.methods,
    )


def extract_ordered_trade_pnls(trades: pl.DataFrame) -> list[Decimal]:
    """Return trade net PnL values ordered by exit time."""
    if len(trades) == 0:
        return []
    ordered = trades.sort("exit_fill_at")
    return [Decimal(str(value)) for value in ordered.get_column("net_pnl").to_list()]


def build_session_day_blocks(trades: pl.DataFrame) -> list[list[int]]:
    """Return trade index blocks grouped by UTC session day."""
    if len(trades) == 0:
        return []
    ordered = trades.sort("exit_fill_at").with_row_index("trade_index")
    ordered = ordered.with_columns(session_day=pl.col("exit_fill_at").dt.date().cast(pl.Utf8))
    blocks: list[list[int]] = []
    for session_day in ordered.get_column("session_day").unique(maintain_order=True).to_list():
        frame = ordered.filter(pl.col("session_day") == session_day)
        blocks.append([int(index) for index in frame.get_column("trade_index").to_list()])
    return blocks


def equity_path_from_pnls(
    *,
    trade_pnls: list[Decimal],
    initial_capital: Decimal,
) -> tuple[list[Decimal], Decimal, Decimal]:
    """Build one equity path and return points, terminal equity, and max drawdown."""
    if not trade_pnls:
        return [], initial_capital, Decimal("0")

    equity_points: list[Decimal] = []
    running_pnl = Decimal("0")
    peak_equity = initial_capital
    max_drawdown = Decimal("0")

    for pnl in trade_pnls:
        running_pnl += pnl
        equity = initial_capital + running_pnl
        equity_points.append(equity)
        if equity > peak_equity:
            peak_equity = equity
        drawdown = equity - peak_equity
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    terminal_equity = equity_points[-1]
    return equity_points, terminal_equity, max_drawdown


def _simulate_paths_for_method(
    *,
    method: MonteCarloMethod,
    trade_pnls: list[Decimal],
    blocks: list[list[int]],
    path_count: int,
    rng: random.Random,
) -> list[list[Decimal]]:
    trade_count = len(trade_pnls)
    if trade_count == 0:
        return [[] for _ in range(path_count)]

    if method is MonteCarloMethod.TRADE_SHUFFLE:
        return _simulate_trade_shuffle_paths(
            trade_pnls=trade_pnls,
            path_count=path_count,
            rng=rng,
        )
    if method is MonteCarloMethod.TRADE_BOOTSTRAP:
        return _simulate_trade_bootstrap_paths(
            trade_pnls=trade_pnls,
            path_count=path_count,
            rng=rng,
        )
    return _simulate_block_bootstrap_paths(
        trade_pnls=trade_pnls,
        blocks=blocks,
        path_count=path_count,
        rng=rng,
    )


def _simulate_trade_shuffle_paths(
    *,
    trade_pnls: list[Decimal],
    path_count: int,
    rng: random.Random,
) -> list[list[Decimal]]:
    trade_count = len(trade_pnls)
    indices = list(range(trade_count))
    paths: list[list[Decimal]] = []
    for _ in range(path_count):
        sampled_indices = indices[:]
        rng.shuffle(sampled_indices)
        paths.append([trade_pnls[index] for index in sampled_indices])
    return paths


def _simulate_trade_bootstrap_paths(
    *,
    trade_pnls: list[Decimal],
    path_count: int,
    rng: random.Random,
) -> list[list[Decimal]]:
    trade_count = len(trade_pnls)
    paths: list[list[Decimal]] = []
    for _ in range(path_count):
        sampled_indices = [rng.randrange(trade_count) for _ in range(trade_count)]
        paths.append([trade_pnls[index] for index in sampled_indices])
    return paths


def _simulate_block_bootstrap_paths(
    *,
    trade_pnls: list[Decimal],
    blocks: list[list[int]],
    path_count: int,
    rng: random.Random,
) -> list[list[Decimal]]:
    if not blocks:
        return [[] for _ in range(path_count)]

    trade_count = len(trade_pnls)
    paths: list[list[Decimal]] = []
    for _ in range(path_count):
        sampled_indices: list[int] = []
        while len(sampled_indices) < trade_count:
            block = blocks[rng.randrange(len(blocks))]
            sampled_indices.extend(block)
        paths.append([trade_pnls[index] for index in sampled_indices[:trade_count]])
    return paths


def _summarize_paths(
    *,
    paths: list[list[Decimal]],
    method: MonteCarloMethod,
    initial_capital: Decimal,
) -> tuple[tuple[MonteCarloPathSummary, ...], tuple[MonteCarloPercentilePoint, ...]]:
    path_summaries: list[MonteCarloPathSummary] = []
    equity_paths: list[list[Decimal]] = []

    for path_index, trade_pnls in enumerate(paths):
        equity_points, terminal_equity, max_drawdown = equity_path_from_pnls(
            trade_pnls=trade_pnls,
            initial_capital=initial_capital,
        )
        equity_paths.append(equity_points)
        net_pnl = terminal_equity - initial_capital
        path_summaries.append(
            MonteCarloPathSummary(
                path_index=path_index,
                method=method.value,
                net_pnl=str(net_pnl),
                terminal_equity=str(terminal_equity),
                max_drawdown=str(max_drawdown),
            )
        )

    percentile_equity = _build_percentile_envelope(equity_paths=equity_paths)
    return tuple(path_summaries), percentile_equity


def _build_percentile_envelope(
    *,
    equity_paths: list[list[Decimal]],
) -> tuple[MonteCarloPercentilePoint, ...]:
    if not equity_paths:
        return ()

    max_length = max(len(path) for path in equity_paths)
    points: list[MonteCarloPercentilePoint] = []
    for trade_index in range(max_length):
        values = [
            path[trade_index] if trade_index < len(path) else path[-1]
            for path in equity_paths
            if path
        ]
        if not values:
            continue
        points.append(
            MonteCarloPercentilePoint(
                trade_index=trade_index,
                p5=str(_percentile(values, 0.05)),
                p50=str(_percentile(values, 0.50)),
                p95=str(_percentile(values, 0.95)),
            )
        )
    return tuple(points)


def _percentile(values: list[Decimal], quantile: float) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    index = int((len(ordered) - 1) * quantile)
    return ordered[index]


def _distribution_summary_from_paths(
    method_result: MonteCarloMethodResult,
) -> DistributionSummary:
    terminal_equities = [
        Decimal(summary.terminal_equity) for summary in method_result.path_summaries
    ]
    net_pnls = [Decimal(summary.net_pnl) for summary in method_result.path_summaries]
    max_drawdowns = [Decimal(summary.max_drawdown) for summary in method_result.path_summaries]
    return DistributionSummary(
        method=method_result.method,
        path_count=method_result.path_count,
        mean_terminal_equity=_mean_decimal(terminal_equities),
        mean_net_pnl=_mean_decimal(net_pnls),
        mean_max_drawdown=_mean_decimal(max_drawdowns),
        p5_terminal_equity=_percentile(terminal_equities, 0.05),
        p50_terminal_equity=_percentile(terminal_equities, 0.50),
        p95_terminal_equity=_percentile(terminal_equities, 0.95),
    )


def _tail_probabilities_from_paths(
    *,
    method_result: MonteCarloMethodResult,
    max_drawdown_threshold: Decimal | None,
) -> TailProbabilityMetrics:
    path_count = len(method_result.path_summaries)
    if path_count == 0:
        return TailProbabilityMetrics(
            method=method_result.method,
            probability_terminal_pnl_negative=Decimal("0"),
            probability_max_drawdown_exceeds_threshold=None,
        )

    negative_count = sum(
        1 for summary in method_result.path_summaries if Decimal(summary.net_pnl) < 0
    )
    negative_probability = Decimal(negative_count) / Decimal(path_count)

    threshold_probability: Decimal | None = None
    if max_drawdown_threshold is not None:
        exceed_count = sum(
            1
            for summary in method_result.path_summaries
            if Decimal(summary.max_drawdown) < max_drawdown_threshold
        )
        threshold_probability = Decimal(exceed_count) / Decimal(path_count)

    return TailProbabilityMetrics(
        method=method_result.method,
        probability_terminal_pnl_negative=negative_probability,
        probability_max_drawdown_exceeds_threshold=threshold_probability,
    )


def _mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def _distribution_summary_to_dict(summary: DistributionSummary) -> dict[str, Any]:
    return {
        "method": summary.method,
        "path_count": summary.path_count,
        "mean_terminal_equity": str(summary.mean_terminal_equity),
        "mean_net_pnl": str(summary.mean_net_pnl),
        "mean_max_drawdown": str(summary.mean_max_drawdown),
        "p5_terminal_equity": str(summary.p5_terminal_equity),
        "p50_terminal_equity": str(summary.p50_terminal_equity),
        "p95_terminal_equity": str(summary.p95_terminal_equity),
    }


def _distribution_summary_from_dict(payload: dict[str, Any]) -> DistributionSummary:
    return DistributionSummary(
        method=str(payload["method"]),
        path_count=int(payload["path_count"]),
        mean_terminal_equity=Decimal(str(payload["mean_terminal_equity"])),
        mean_net_pnl=Decimal(str(payload["mean_net_pnl"])),
        mean_max_drawdown=Decimal(str(payload["mean_max_drawdown"])),
        p5_terminal_equity=Decimal(str(payload["p5_terminal_equity"])),
        p50_terminal_equity=Decimal(str(payload["p50_terminal_equity"])),
        p95_terminal_equity=Decimal(str(payload["p95_terminal_equity"])),
    )


def _tail_probability_to_dict(metrics: TailProbabilityMetrics) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "method": metrics.method,
        "probability_terminal_pnl_negative": str(metrics.probability_terminal_pnl_negative),
    }
    if metrics.probability_max_drawdown_exceeds_threshold is not None:
        payload["probability_max_drawdown_exceeds_threshold"] = str(
            metrics.probability_max_drawdown_exceeds_threshold
        )
    return payload


def _tail_probability_from_dict(payload: dict[str, Any]) -> TailProbabilityMetrics:
    threshold = payload.get("probability_max_drawdown_exceeds_threshold")
    return TailProbabilityMetrics(
        method=str(payload["method"]),
        probability_terminal_pnl_negative=Decimal(
            str(payload["probability_terminal_pnl_negative"])
        ),
        probability_max_drawdown_exceeds_threshold=(
            Decimal(str(threshold)) if threshold is not None else None
        ),
    )
