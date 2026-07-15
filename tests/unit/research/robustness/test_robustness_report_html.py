"""Tests for robustness HTML dashboard report rendering."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from trading_framework.research.robustness.analytics.diagnostics import (
    PnlConcentrationMetrics,
    StatisticalDiagnosticsAnalytics,
    TemporalStabilityMetrics,
)
from trading_framework.research.robustness.analytics.monte_carlo import (
    DistributionSummary,
    MonteCarloAnalytics,
    TailProbabilityMetrics,
)
from trading_framework.research.robustness.report import RobustnessReportViewModel
from trading_framework.research.robustness.report_html import render_robustness_report
from trading_framework.research.robustness.verdict import (
    RobustnessVerdict,
    VerdictKind,
)
from trading_framework.research.robustness.verdict_thresholds import VerdictThresholds


def _sample_view_model() -> RobustnessReportViewModel:
    verdict = RobustnessVerdict(
        experiment_id="exp-report",
        verdict=VerdictKind.PASS,
        summary="Experiment exp-report passed all configured validation gates.",
        strengths=("MC gate passed (0.1)",),
        weaknesses=(),
        blocking_issues=(),
        assumptions_fingerprint="assumptions-fp",
        best_ranked_config_id=None,
        gate_results=(),
    )
    diagnostics = StatisticalDiagnosticsAnalytics(
        experiment_id="exp-report",
        reference_strategy_run_id="run-1",
        temporal_stability=TemporalStabilityMetrics(
            bucket_mode="MONTH",
            buckets=(),
            bucket_count=1,
            net_pnl_range=Decimal("10"),
            net_pnl_coefficient_of_variation=Decimal("0.1"),
        ),
        pnl_concentration=PnlConcentrationMetrics(
            total_net_pnl=Decimal("100"),
            top_k_trades=2,
            top_k_days=2,
            top_trades_share=Decimal("0.3"),
            top_days_share=Decimal("0.25"),
            top_trade_ids=("t1",),
            top_session_days=("2024-01-01",),
        ),
        is_oos_degradation=None,
    )
    monte_carlo = MonteCarloAnalytics(
        experiment_id="exp-report",
        reference_strategy_run_id="run-1",
        rng_seed=7,
        distribution_summaries=(
            DistributionSummary(
                method="TRADE_BOOTSTRAP",
                path_count=10,
                mean_terminal_equity=Decimal("101000"),
                mean_net_pnl=Decimal("1000"),
                mean_max_drawdown=Decimal("-200"),
                p5_terminal_equity=Decimal("99000"),
                p50_terminal_equity=Decimal("101000"),
                p95_terminal_equity=Decimal("103000"),
            ),
        ),
        tail_probabilities=(
            TailProbabilityMetrics(
                method="TRADE_BOOTSTRAP",
                probability_terminal_pnl_negative=Decimal("0.1"),
                probability_max_drawdown_exceeds_threshold=Decimal("0.05"),
            ),
        ),
        method_results=(),
    )
    return RobustnessReportViewModel(
        experiment_id="exp-report",
        kinds=("MONTE_CARLO", "STATISTICAL_DIAGNOSTICS"),
        dataset_ref="ES.c.0/ohlcv/1m/csv/fixture@1",
        strategy_template_id="high_vol_higher_low_fixed_exit",
        timeframe="1m",
        framework_version="0.0.0",
        simulation_assumptions_fingerprint="assumptions-fp",
        verdict=verdict,
        verdict_thresholds=VerdictThresholds(max_mc_loss_probability=Decimal("0.5")),
        parameter_sweep=None,
        walk_forward=None,
        stress=None,
        monte_carlo=monte_carlo,
        diagnostics=diagnostics,
    )


def test_render_robustness_report_writes_dashboard_html(tmp_path: Path) -> None:
    output_path = tmp_path / "robustness_report.html"
    render_robustness_report(_sample_view_model(), output_path)
    content = output_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "verdict-hero pass" in content
    assert "Monte Carlo simulation" in content
    assert "Statistical health checks" in content
    assert "section-intro" in content
    assert "cell_" not in content
    assert "lightweight-charts" in content
    assert "report-data" in content
