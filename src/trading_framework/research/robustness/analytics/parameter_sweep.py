"""Parameter sweep analytics — ranking, neighbor stability, heatmaps, isolated optima."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.experiment import ParameterSweepAxis, ParameterSweepSpec


class ParameterSweepAnalyticsError(ValidationError):
    """Raised when parameter sweep analytics inputs are invalid."""


class SweepMetric(StrEnum):
    """Ranking metric for parameter sweep cells."""

    NET_PNL = "net_pnl"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    FINAL_EQUITY = "final_equity"


_DEFAULT_ISOLATION_NEIGHBOR_RATIO = Decimal("0.5")


@dataclass(frozen=True, slots=True)
class SweepRunMetrics:
    """Read-only metrics for one completed sweep cell."""

    config_id: str
    config_fingerprint: str
    parameter_overrides: dict[str, str]
    strategy_run_id: str
    summary: StrategyRunSummary

    def metric_value(self, metric: SweepMetric) -> Decimal | float | None:
        if metric is SweepMetric.NET_PNL:
            return self.summary.net_pnl
        if metric is SweepMetric.MAX_DRAWDOWN:
            return self.summary.max_drawdown
        if metric is SweepMetric.WIN_RATE:
            return self.summary.win_rate
        return self.summary.final_equity


@dataclass(frozen=True, slots=True)
class SweepRankingRow:
    """One ranked sweep cell."""

    rank: int
    config_id: str
    config_fingerprint: str
    parameter_overrides: dict[str, str]
    strategy_run_id: str
    metric: SweepMetric
    metric_value: Decimal | float | None
    net_pnl: Decimal
    max_drawdown: Decimal
    win_rate: float | None
    trade_count: int


@dataclass(frozen=True, slots=True)
class NeighborStabilityRow:
    """Neighbor sensitivity for one sweep cell."""

    config_id: str
    parameter_overrides: dict[str, str]
    net_pnl: Decimal
    neighbor_count: int
    neighbor_mean_net_pnl: Decimal | None
    neighbor_min_net_pnl: Decimal | None
    neighbor_max_net_pnl: Decimal | None
    stability_score: float
    is_stable: bool


@dataclass(frozen=True, slots=True)
class ParameterHeatmapView:
    """Grid view model for one metric over one or two swept axes."""

    metric: SweepMetric
    x_axis: str
    y_axis: str | None
    x_values: tuple[str, ...]
    y_values: tuple[str, ...] | None
    values: tuple[tuple[float | None, ...], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric.value,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "x_values": list(self.x_values),
            "y_values": list(self.y_values) if self.y_values is not None else None,
            "values": [list(row) for row in self.values],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ParameterHeatmapView:
        y_values_payload = payload.get("y_values")
        return cls(
            metric=SweepMetric(str(payload["metric"])),
            x_axis=str(payload["x_axis"]),
            y_axis=str(payload["y_axis"]) if payload.get("y_axis") is not None else None,
            x_values=tuple(str(value) for value in payload["x_values"]),
            y_values=(
                tuple(str(value) for value in y_values_payload)
                if y_values_payload is not None
                else None
            ),
            values=tuple(
                tuple(None if value is None else float(value) for value in row)
                for row in payload["values"]
            ),
        )


@dataclass(frozen=True, slots=True)
class IsolatedOptimumFlag:
    """Detection result for one sweep cell."""

    config_id: str
    rank: int
    net_pnl: Decimal
    neighbor_mean_net_pnl: Decimal | None
    is_local_maximum: bool
    is_isolated_optimum: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ParameterSweepAnalytics:
    """Bundled parameter sweep analytics for one experiment."""

    experiment_id: str
    ranking_metric: SweepMetric
    rankings: tuple[SweepRankingRow, ...]
    neighbor_stability: tuple[NeighborStabilityRow, ...]
    heatmaps: tuple[ParameterHeatmapView, ...]
    isolated_optima: tuple[IsolatedOptimumFlag, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "ranking_metric": self.ranking_metric.value,
            "rankings": [_ranking_row_to_dict(row) for row in self.rankings],
            "neighbor_stability": [_neighbor_row_to_dict(row) for row in self.neighbor_stability],
            "heatmaps": [heatmap.to_dict() for heatmap in self.heatmaps],
            "isolated_optima": [_isolated_flag_to_dict(flag) for flag in self.isolated_optima],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ParameterSweepAnalytics:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            ranking_metric=SweepMetric(str(payload["ranking_metric"])),
            rankings=tuple(_ranking_row_from_dict(row) for row in payload["rankings"]),
            neighbor_stability=tuple(
                _neighbor_row_from_dict(row) for row in payload["neighbor_stability"]
            ),
            heatmaps=tuple(
                ParameterHeatmapView.from_dict(heatmap) for heatmap in payload["heatmaps"]
            ),
            isolated_optima=tuple(
                _isolated_flag_from_dict(flag) for flag in payload["isolated_optima"]
            ),
        )


def build_parameter_sweep_analytics(
    *,
    experiment_id: str,
    parameter_sweep: ParameterSweepSpec,
    completed_runs: tuple[SweepRunMetrics, ...],
    ranking_metric: SweepMetric = SweepMetric.NET_PNL,
    stability_threshold: float = 0.7,
    isolation_neighbor_ratio: Decimal = _DEFAULT_ISOLATION_NEIGHBOR_RATIO,
) -> ParameterSweepAnalytics:
    """Compute ranking, neighbor stability, heatmaps, and isolated optima."""
    if not completed_runs:
        msg = "parameter sweep analytics requires at least one completed run"
        raise ParameterSweepAnalyticsError(msg)
    rankings = rank_parameter_sweep(
        completed_runs=completed_runs,
        ranking_metric=ranking_metric,
    )
    neighbor_stability = analyze_neighbor_stability(
        parameter_sweep=parameter_sweep,
        completed_runs=completed_runs,
        stability_threshold=stability_threshold,
    )
    heatmaps = build_parameter_heatmaps(
        parameter_sweep=parameter_sweep,
        completed_runs=completed_runs,
        ranking_metric=ranking_metric,
    )
    isolated_optima = detect_isolated_optima(
        parameter_sweep=parameter_sweep,
        rankings=rankings,
        neighbor_stability=neighbor_stability,
        isolation_neighbor_ratio=isolation_neighbor_ratio,
    )
    return ParameterSweepAnalytics(
        experiment_id=experiment_id,
        ranking_metric=ranking_metric,
        rankings=rankings,
        neighbor_stability=neighbor_stability,
        heatmaps=heatmaps,
        isolated_optima=isolated_optima,
    )


def rank_parameter_sweep(
    *,
    completed_runs: tuple[SweepRunMetrics, ...],
    ranking_metric: SweepMetric = SweepMetric.NET_PNL,
) -> tuple[SweepRankingRow, ...]:
    """Rank completed sweep cells by one metric (higher is better)."""
    rows: list[SweepRankingRow] = []
    for run in completed_runs:
        rows.append(
            SweepRankingRow(
                rank=0,
                config_id=run.config_id,
                config_fingerprint=run.config_fingerprint,
                parameter_overrides=run.parameter_overrides,
                strategy_run_id=run.strategy_run_id,
                metric=ranking_metric,
                metric_value=run.metric_value(ranking_metric),
                net_pnl=run.summary.net_pnl,
                max_drawdown=run.summary.max_drawdown,
                win_rate=run.summary.win_rate,
                trade_count=run.summary.trade_count,
            )
        )
    rows.sort(key=_ranking_sort_key, reverse=True)
    return tuple(
        SweepRankingRow(
            rank=index + 1,
            config_id=row.config_id,
            config_fingerprint=row.config_fingerprint,
            parameter_overrides=row.parameter_overrides,
            strategy_run_id=row.strategy_run_id,
            metric=row.metric,
            metric_value=row.metric_value,
            net_pnl=row.net_pnl,
            max_drawdown=row.max_drawdown,
            win_rate=row.win_rate,
            trade_count=row.trade_count,
        )
        for index, row in enumerate(rows)
    )


def analyze_neighbor_stability(
    *,
    parameter_sweep: ParameterSweepSpec,
    completed_runs: tuple[SweepRunMetrics, ...],
    stability_threshold: float = 0.7,
) -> tuple[NeighborStabilityRow, ...]:
    """Measure local grid sensitivity using adjacent parameter neighbors."""
    if stability_threshold < 0 or stability_threshold > 1:
        msg = "stability_threshold must be between 0 and 1"
        raise ParameterSweepAnalyticsError(msg)

    index = _build_grid_index(parameter_sweep, completed_runs)
    rows: list[NeighborStabilityRow] = []
    for run in completed_runs:
        coordinates = index.coordinates_for(run.config_id)
        neighbor_pnls: list[Decimal] = []
        for neighbor_id in index.neighbor_ids(coordinates):
            neighbor_pnl = index.net_pnl_for(neighbor_id)
            if neighbor_pnl is not None:
                neighbor_pnls.append(neighbor_pnl)
        neighbor_count = len(neighbor_pnls)
        if neighbor_count == 0:
            rows.append(
                NeighborStabilityRow(
                    config_id=run.config_id,
                    parameter_overrides=run.parameter_overrides,
                    net_pnl=run.summary.net_pnl,
                    neighbor_count=0,
                    neighbor_mean_net_pnl=None,
                    neighbor_min_net_pnl=None,
                    neighbor_max_net_pnl=None,
                    stability_score=0.0,
                    is_stable=False,
                )
            )
            continue

        neighbor_mean = _mean_decimal(neighbor_pnls)
        stability_score = _stability_score(run.summary.net_pnl, neighbor_pnls)
        rows.append(
            NeighborStabilityRow(
                config_id=run.config_id,
                parameter_overrides=run.parameter_overrides,
                net_pnl=run.summary.net_pnl,
                neighbor_count=neighbor_count,
                neighbor_mean_net_pnl=neighbor_mean,
                neighbor_min_net_pnl=min(neighbor_pnls),
                neighbor_max_net_pnl=max(neighbor_pnls),
                stability_score=stability_score,
                is_stable=stability_score >= stability_threshold,
            )
        )
    return tuple(rows)


def build_parameter_heatmaps(
    *,
    parameter_sweep: ParameterSweepSpec,
    completed_runs: tuple[SweepRunMetrics, ...],
    ranking_metric: SweepMetric = SweepMetric.NET_PNL,
) -> tuple[ParameterHeatmapView, ...]:
    """Build heatmap view models for each swept axis pair."""
    if len(parameter_sweep.axes) == 1:
        axis = parameter_sweep.axes[0]
        return (
            _build_one_axis_heatmap(
                axis=axis,
                completed_runs=completed_runs,
                ranking_metric=ranking_metric,
            ),
        )

    heatmaps: list[ParameterHeatmapView] = []
    for x_axis, y_axis in itertools.combinations(parameter_sweep.axes, 2):
        heatmaps.append(
            _build_two_axis_heatmap(
                x_axis=x_axis,
                y_axis=y_axis,
                parameter_sweep=parameter_sweep,
                completed_runs=completed_runs,
                ranking_metric=ranking_metric,
            )
        )
    return tuple(heatmaps)


def detect_isolated_optima(
    *,
    parameter_sweep: ParameterSweepSpec,
    rankings: tuple[SweepRankingRow, ...],
    neighbor_stability: tuple[NeighborStabilityRow, ...],
    isolation_neighbor_ratio: Decimal = _DEFAULT_ISOLATION_NEIGHBOR_RATIO,
) -> tuple[IsolatedOptimumFlag, ...]:
    """Flag local maxima surrounded by materially weaker neighbors."""
    if isolation_neighbor_ratio < 0 or isolation_neighbor_ratio > 1:
        msg = "isolation_neighbor_ratio must be between 0 and 1"
        raise ParameterSweepAnalyticsError(msg)

    stability_by_id = {row.config_id: row for row in neighbor_stability}
    index = _build_grid_index_from_rankings(parameter_sweep, rankings)
    flags: list[IsolatedOptimumFlag] = []

    for row in rankings:
        coordinates = index.coordinates_for(row.config_id)
        neighbor_values: list[Decimal] = []
        for neighbor_id in index.neighbor_ids(coordinates):
            neighbor_value = index.metric_for(neighbor_id)
            if neighbor_value is not None:
                neighbor_values.append(neighbor_value)
        cell_value = _metric_as_decimal(row.metric_value)
        is_local_maximum = bool(neighbor_values) and all(
            cell_value >= neighbor for neighbor in neighbor_values
        )
        stability = stability_by_id[row.config_id]
        neighbor_mean = stability.neighbor_mean_net_pnl
        is_isolated = False
        reason = "not_local_maximum"
        if is_local_maximum and neighbor_mean is not None:
            if cell_value > 0 and neighbor_mean <= cell_value * isolation_neighbor_ratio:
                is_isolated = True
                reason = "neighbors_below_ratio_threshold"
            elif cell_value > 0 and all(
                neighbor < cell_value * isolation_neighbor_ratio for neighbor in neighbor_values
            ):
                is_isolated = True
                reason = "all_neighbors_materially_weaker"
            elif cell_value <= 0 and neighbor_mean < cell_value:
                is_isolated = True
                reason = "local_maximum_in_negative_region"

        flags.append(
            IsolatedOptimumFlag(
                config_id=row.config_id,
                rank=row.rank,
                net_pnl=row.net_pnl,
                neighbor_mean_net_pnl=neighbor_mean,
                is_local_maximum=is_local_maximum,
                is_isolated_optimum=is_isolated,
                reason=reason,
            )
        )
    return tuple(flags)


@dataclass(frozen=True, slots=True)
class _GridIndex:
    axis_names: tuple[str, ...]
    axis_values: tuple[tuple[str, ...], ...]
    coordinates_by_config_id: dict[str, tuple[int, ...]]
    config_id_by_coordinates: dict[tuple[int, ...], str]
    metric_by_config_id: dict[str, Decimal]

    def coordinates_for(self, config_id: str) -> tuple[int, ...]:
        return self.coordinates_by_config_id[config_id]

    def neighbor_ids(self, coordinates: tuple[int, ...]) -> tuple[str, ...]:
        neighbor_ids: list[str] = []
        for axis_index, axis_size in enumerate(self.axis_sizes):
            for delta in (-1, 1):
                neighbor_coord = list(coordinates)
                next_index = coordinates[axis_index] + delta
                if 0 <= next_index < axis_size:
                    neighbor_coord[axis_index] = next_index
                    config_id = self.config_id_by_coordinates.get(tuple(neighbor_coord))
                    if config_id is not None:
                        neighbor_ids.append(config_id)
        return tuple(neighbor_ids)

    @property
    def axis_sizes(self) -> tuple[int, ...]:
        return tuple(len(values) for values in self.axis_values)

    def net_pnl_for(self, config_id: str) -> Decimal | None:
        return self.metric_by_config_id.get(config_id)

    def metric_for(self, config_id: str) -> Decimal | None:
        return self.metric_by_config_id.get(config_id)


def _build_grid_index(
    parameter_sweep: ParameterSweepSpec,
    completed_runs: tuple[SweepRunMetrics, ...],
) -> _GridIndex:
    return _build_grid_index_from_values(
        parameter_sweep=parameter_sweep,
        config_values={run.config_id: run.summary.net_pnl for run in completed_runs},
        coordinates_by_config_id={
            run.config_id: _coordinates_for_overrides(
                parameter_sweep,
                run.parameter_overrides,
            )
            for run in completed_runs
        },
    )


def _build_grid_index_from_rankings(
    parameter_sweep: ParameterSweepSpec,
    rankings: tuple[SweepRankingRow, ...],
) -> _GridIndex:
    return _build_grid_index_from_values(
        parameter_sweep=parameter_sweep,
        config_values={row.config_id: _metric_as_decimal(row.metric_value) for row in rankings},
        coordinates_by_config_id={
            row.config_id: _coordinates_for_overrides(
                parameter_sweep,
                row.parameter_overrides,
            )
            for row in rankings
        },
    )


def _build_grid_index_from_values(
    *,
    parameter_sweep: ParameterSweepSpec,
    config_values: dict[str, Decimal],
    coordinates_by_config_id: dict[str, tuple[int, ...]],
) -> _GridIndex:
    config_id_by_coordinates = {
        coordinates: config_id for config_id, coordinates in coordinates_by_config_id.items()
    }
    return _GridIndex(
        axis_names=tuple(axis.name for axis in parameter_sweep.axes),
        axis_values=tuple(axis.values for axis in parameter_sweep.axes),
        coordinates_by_config_id=coordinates_by_config_id,
        config_id_by_coordinates=config_id_by_coordinates,
        metric_by_config_id=config_values,
    )


def _coordinates_for_overrides(
    parameter_sweep: ParameterSweepSpec,
    overrides: dict[str, str],
) -> tuple[int, ...]:
    coordinates: list[int] = []
    for axis in parameter_sweep.axes:
        value = overrides.get(axis.name, axis.values[0])
        coordinates.append(axis.values.index(value))
    return tuple(coordinates)


def _build_one_axis_heatmap(
    *,
    axis: ParameterSweepAxis,
    completed_runs: tuple[SweepRunMetrics, ...],
    ranking_metric: SweepMetric,
) -> ParameterHeatmapView:
    values_by_axis: dict[str, list[float]] = {value: [] for value in axis.values}
    for run in completed_runs:
        axis_value = run.parameter_overrides.get(axis.name, axis.values[0])
        metric = run.metric_value(ranking_metric)
        if metric is None:
            continue
        values_by_axis[axis_value].append(float(metric))

    row = tuple(_mean_or_none(values_by_axis[value]) for value in axis.values)
    return ParameterHeatmapView(
        metric=ranking_metric,
        x_axis=axis.name,
        y_axis=None,
        x_values=axis.values,
        y_values=None,
        values=(row,),
    )


def _build_two_axis_heatmap(
    *,
    x_axis: ParameterSweepAxis,
    y_axis: ParameterSweepAxis,
    parameter_sweep: ParameterSweepSpec,
    completed_runs: tuple[SweepRunMetrics, ...],
    ranking_metric: SweepMetric,
) -> ParameterHeatmapView:
    buckets: dict[tuple[str, str], list[float]] = {
        (x_value, y_value): [] for x_value in x_axis.values for y_value in y_axis.values
    }
    for run in completed_runs:
        x_value = run.parameter_overrides.get(x_axis.name, x_axis.values[0])
        y_value = run.parameter_overrides.get(y_axis.name, y_axis.values[0])
        metric = run.metric_value(ranking_metric)
        if metric is None:
            continue
        buckets[(x_value, y_value)].append(float(metric))

    values = tuple(
        tuple(_mean_or_none(buckets[(x_value, y_value)]) for x_value in x_axis.values)
        for y_value in y_axis.values
    )
    return ParameterHeatmapView(
        metric=ranking_metric,
        x_axis=x_axis.name,
        y_axis=y_axis.name,
        x_values=x_axis.values,
        y_values=y_axis.values,
        values=values,
    )


def _ranking_sort_key(row: SweepRankingRow) -> tuple[float, str]:
    metric = row.metric_value
    if metric is None:
        return (float("-inf"), row.config_id)
    return (float(metric), row.config_id)


def _stability_score(cell_pnl: Decimal, neighbor_pnls: list[Decimal]) -> float:
    denom = max(abs(cell_pnl), Decimal("1"))
    deviations = [float(abs(neighbor - cell_pnl) / denom) for neighbor in neighbor_pnls]
    mean_deviation = sum(deviations) / len(deviations)
    return max(0.0, 1.0 - mean_deviation)


def _mean_decimal(values: list[Decimal]) -> Decimal:
    total = sum(values, start=Decimal("0"))
    return total / Decimal(len(values))


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _metric_as_decimal(metric: Decimal | float | None) -> Decimal:
    if metric is None:
        return Decimal("0")
    if isinstance(metric, Decimal):
        return metric
    return Decimal(str(metric))


def _ranking_row_to_dict(row: SweepRankingRow) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "config_id": row.config_id,
        "config_fingerprint": row.config_fingerprint,
        "parameter_overrides": row.parameter_overrides,
        "strategy_run_id": row.strategy_run_id,
        "metric": row.metric.value,
        "metric_value": _serialize_metric(row.metric_value),
        "net_pnl": str(row.net_pnl),
        "max_drawdown": str(row.max_drawdown),
        "win_rate": row.win_rate,
        "trade_count": row.trade_count,
    }


def _ranking_row_from_dict(payload: dict[str, Any]) -> SweepRankingRow:
    metric_value = payload.get("metric_value")
    return SweepRankingRow(
        rank=int(payload["rank"]),
        config_id=str(payload["config_id"]),
        config_fingerprint=str(payload["config_fingerprint"]),
        parameter_overrides={
            str(key): str(value) for key, value in payload["parameter_overrides"].items()
        },
        strategy_run_id=str(payload["strategy_run_id"]),
        metric=SweepMetric(str(payload["metric"])),
        metric_value=(
            None
            if metric_value is None
            else Decimal(str(metric_value))
            if payload["metric"] != SweepMetric.WIN_RATE.value
            else float(metric_value)
        ),
        net_pnl=Decimal(str(payload["net_pnl"])),
        max_drawdown=Decimal(str(payload["max_drawdown"])),
        win_rate=(float(payload["win_rate"]) if payload.get("win_rate") is not None else None),
        trade_count=int(payload["trade_count"]),
    )


def _neighbor_row_to_dict(row: NeighborStabilityRow) -> dict[str, Any]:
    return {
        "config_id": row.config_id,
        "parameter_overrides": row.parameter_overrides,
        "net_pnl": str(row.net_pnl),
        "neighbor_count": row.neighbor_count,
        "neighbor_mean_net_pnl": (
            str(row.neighbor_mean_net_pnl) if row.neighbor_mean_net_pnl is not None else None
        ),
        "neighbor_min_net_pnl": (
            str(row.neighbor_min_net_pnl) if row.neighbor_min_net_pnl is not None else None
        ),
        "neighbor_max_net_pnl": (
            str(row.neighbor_max_net_pnl) if row.neighbor_max_net_pnl is not None else None
        ),
        "stability_score": row.stability_score,
        "is_stable": row.is_stable,
    }


def _neighbor_row_from_dict(payload: dict[str, Any]) -> NeighborStabilityRow:
    return NeighborStabilityRow(
        config_id=str(payload["config_id"]),
        parameter_overrides={
            str(key): str(value) for key, value in payload["parameter_overrides"].items()
        },
        net_pnl=Decimal(str(payload["net_pnl"])),
        neighbor_count=int(payload["neighbor_count"]),
        neighbor_mean_net_pnl=(
            Decimal(str(payload["neighbor_mean_net_pnl"]))
            if payload.get("neighbor_mean_net_pnl") is not None
            else None
        ),
        neighbor_min_net_pnl=(
            Decimal(str(payload["neighbor_min_net_pnl"]))
            if payload.get("neighbor_min_net_pnl") is not None
            else None
        ),
        neighbor_max_net_pnl=(
            Decimal(str(payload["neighbor_max_net_pnl"]))
            if payload.get("neighbor_max_net_pnl") is not None
            else None
        ),
        stability_score=float(payload["stability_score"]),
        is_stable=bool(payload["is_stable"]),
    )


def _isolated_flag_to_dict(flag: IsolatedOptimumFlag) -> dict[str, Any]:
    return {
        "config_id": flag.config_id,
        "rank": flag.rank,
        "net_pnl": str(flag.net_pnl),
        "neighbor_mean_net_pnl": (
            str(flag.neighbor_mean_net_pnl) if flag.neighbor_mean_net_pnl is not None else None
        ),
        "is_local_maximum": flag.is_local_maximum,
        "is_isolated_optimum": flag.is_isolated_optimum,
        "reason": flag.reason,
    }


def _isolated_flag_from_dict(payload: dict[str, Any]) -> IsolatedOptimumFlag:
    return IsolatedOptimumFlag(
        config_id=str(payload["config_id"]),
        rank=int(payload["rank"]),
        net_pnl=Decimal(str(payload["net_pnl"])),
        neighbor_mean_net_pnl=(
            Decimal(str(payload["neighbor_mean_net_pnl"]))
            if payload.get("neighbor_mean_net_pnl") is not None
            else None
        ),
        is_local_maximum=bool(payload["is_local_maximum"]),
        is_isolated_optimum=bool(payload["is_isolated_optimum"]),
        reason=str(payload["reason"]),
    )


def _serialize_metric(metric: Decimal | float | None) -> str | float | None:
    if metric is None:
        return None
    if isinstance(metric, Decimal):
        return str(metric)
    return metric
