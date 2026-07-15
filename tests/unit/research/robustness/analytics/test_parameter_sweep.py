"""Unit tests for parameter sweep analytics primitives."""

from __future__ import annotations

from decimal import Decimal

from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.analytics.parameter_sweep import (
    SweepMetric,
    SweepRunMetrics,
    analyze_neighbor_stability,
    build_parameter_heatmaps,
    build_parameter_sweep_analytics,
    detect_isolated_optima,
    rank_parameter_sweep,
)
from trading_framework.research.robustness.experiment import ParameterSweepAxis, ParameterSweepSpec


def _summary(*, net_pnl: str) -> StrategyRunSummary:
    return StrategyRunSummary(
        trade_count=10,
        win_count=6,
        loss_count=4,
        win_rate=0.6,
        gross_pnl=Decimal(net_pnl),
        net_pnl=Decimal(net_pnl),
        total_commission=Decimal("0"),
        max_drawdown=Decimal("-100"),
        final_equity=Decimal("10000") + Decimal(net_pnl),
    )


def _run(
    *,
    config_id: str,
    exit_after_bars: str,
    volatility_period: str,
    net_pnl: str,
) -> SweepRunMetrics:
    return SweepRunMetrics(
        config_id=config_id,
        config_fingerprint=config_id,
        parameter_overrides={
            "exit_after_bars": exit_after_bars,
            "volatility_period": volatility_period,
        },
        strategy_run_id=f"run-{config_id}",
        summary=_summary(net_pnl=net_pnl),
    )


def _two_by_two_spec() -> ParameterSweepSpec:
    return ParameterSweepSpec(
        axes=(
            ParameterSweepAxis(name="exit_after_bars", values=("5", "10")),
            ParameterSweepAxis(name="volatility_period", values=("14", "20")),
        )
    )


def test_rank_parameter_sweep_orders_by_net_pnl_desc() -> None:
    runs = (
        _run(config_id="a", exit_after_bars="5", volatility_period="14", net_pnl="100"),
        _run(config_id="b", exit_after_bars="10", volatility_period="14", net_pnl="300"),
        _run(config_id="c", exit_after_bars="5", volatility_period="20", net_pnl="200"),
    )

    rankings = rank_parameter_sweep(completed_runs=runs)

    assert [row.config_id for row in rankings] == ["b", "c", "a"]
    assert [row.rank for row in rankings] == [1, 2, 3]


def test_analyze_neighbor_stability_scores_plateau_higher_than_peak() -> None:
    spec = _two_by_two_spec()
    runs = (
        _run(config_id="plateau_a", exit_after_bars="5", volatility_period="14", net_pnl="100"),
        _run(config_id="plateau_b", exit_after_bars="10", volatility_period="14", net_pnl="105"),
        _run(config_id="plateau_c", exit_after_bars="5", volatility_period="20", net_pnl="98"),
        _run(config_id="peak", exit_after_bars="10", volatility_period="20", net_pnl="500"),
    )
    rows = analyze_neighbor_stability(parameter_sweep=spec, completed_runs=runs)
    by_id = {row.config_id: row for row in rows}

    assert by_id["peak"].stability_score < by_id["plateau_a"].stability_score
    assert by_id["plateau_a"].is_stable is True
    assert by_id["peak"].is_stable is False


def test_build_parameter_heatmaps_returns_matrix_for_two_axes() -> None:
    spec = _two_by_two_spec()
    runs = (
        _run(config_id="a", exit_after_bars="5", volatility_period="14", net_pnl="100"),
        _run(config_id="b", exit_after_bars="10", volatility_period="14", net_pnl="200"),
        _run(config_id="c", exit_after_bars="5", volatility_period="20", net_pnl="300"),
        _run(config_id="d", exit_after_bars="10", volatility_period="20", net_pnl="400"),
    )

    heatmaps = build_parameter_heatmaps(
        parameter_sweep=spec,
        completed_runs=runs,
        ranking_metric=SweepMetric.NET_PNL,
    )

    assert len(heatmaps) == 1
    heatmap = heatmaps[0]
    assert heatmap.x_axis == "exit_after_bars"
    assert heatmap.y_axis == "volatility_period"
    assert heatmap.values == ((100.0, 200.0), (300.0, 400.0))


def test_detect_isolated_optima_flags_local_peak_with_weak_neighbors() -> None:
    spec = _two_by_two_spec()
    runs = (
        _run(config_id="plateau_a", exit_after_bars="5", volatility_period="14", net_pnl="100"),
        _run(config_id="plateau_b", exit_after_bars="10", volatility_period="14", net_pnl="105"),
        _run(config_id="plateau_c", exit_after_bars="5", volatility_period="20", net_pnl="98"),
        _run(config_id="peak", exit_after_bars="10", volatility_period="20", net_pnl="500"),
    )
    rankings = rank_parameter_sweep(completed_runs=runs)
    neighbor_stability = analyze_neighbor_stability(parameter_sweep=spec, completed_runs=runs)
    flags = detect_isolated_optima(
        parameter_sweep=spec,
        rankings=rankings,
        neighbor_stability=neighbor_stability,
    )
    by_id = {flag.config_id: flag for flag in flags}

    assert by_id["peak"].is_local_maximum is True
    assert by_id["peak"].is_isolated_optimum is True
    assert by_id["plateau_a"].is_isolated_optimum is False


def test_parameter_sweep_analytics_roundtrip_dict() -> None:
    spec = _two_by_two_spec()
    runs = (
        _run(config_id="a", exit_after_bars="5", volatility_period="14", net_pnl="100"),
        _run(config_id="b", exit_after_bars="10", volatility_period="14", net_pnl="200"),
    )
    analytics = build_parameter_sweep_analytics(
        experiment_id="exp-test",
        parameter_sweep=spec,
        completed_runs=runs,
    )
    restored = type(analytics).from_dict(analytics.to_dict())
    assert restored.experiment_id == analytics.experiment_id
    assert len(restored.rankings) == 2
    assert len(restored.heatmaps) == 1
