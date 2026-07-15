"""Unit tests for robustness verdict evaluation."""

from __future__ import annotations

from decimal import Decimal

from trading_framework.research.robustness.analytics.diagnostics import (
    PnlConcentrationMetrics,
    StatisticalDiagnosticsAnalytics,
    TemporalStabilityMetrics,
)
from trading_framework.research.robustness.analytics.monte_carlo import (
    MonteCarloAnalytics,
    TailProbabilityMetrics,
)
from trading_framework.research.robustness.verdict import (
    VerdictEvaluationContext,
    VerdictKind,
    evaluate_robustness_verdict,
)
from trading_framework.research.robustness.verdict_thresholds import VerdictThresholds


def test_evaluate_robustness_verdict_passes_with_no_thresholds() -> None:
    verdict = evaluate_robustness_verdict(
        experiment_id="exp-1",
        assumptions_fingerprint="fp-1",
        thresholds=None,
        context=VerdictEvaluationContext(),
    )
    assert verdict.verdict is VerdictKind.PASS


def test_evaluate_robustness_verdict_conditional_on_mc_loss_probability() -> None:
    diagnostics = StatisticalDiagnosticsAnalytics(
        experiment_id="exp-1",
        reference_strategy_run_id="run-1",
        temporal_stability=TemporalStabilityMetrics(
            bucket_mode="MONTH",
            buckets=(),
            bucket_count=0,
            net_pnl_range=Decimal("0"),
            net_pnl_coefficient_of_variation=None,
        ),
        pnl_concentration=PnlConcentrationMetrics(
            total_net_pnl=Decimal("100"),
            top_k_trades=1,
            top_k_days=1,
            top_trades_share=Decimal("0.2"),
            top_days_share=Decimal("0.2"),
            top_trade_ids=(),
            top_session_days=(),
        ),
        is_oos_degradation=None,
    )
    monte_carlo = MonteCarloAnalytics(
        experiment_id="exp-1",
        reference_strategy_run_id="run-1",
        rng_seed=1,
        distribution_summaries=(),
        tail_probabilities=(
            TailProbabilityMetrics(
                method="TRADE_BOOTSTRAP",
                probability_terminal_pnl_negative=Decimal("0.4"),
                probability_max_drawdown_exceeds_threshold=None,
            ),
        ),
        method_results=(),
    )
    verdict = evaluate_robustness_verdict(
        experiment_id="exp-1",
        assumptions_fingerprint="fp-1",
        thresholds=VerdictThresholds(max_mc_loss_probability=Decimal("0.2")),
        context=VerdictEvaluationContext(
            monte_carlo=monte_carlo,
            diagnostics=diagnostics,
        ),
    )
    assert verdict.verdict is VerdictKind.CONDITIONAL
    assert verdict.weaknesses
