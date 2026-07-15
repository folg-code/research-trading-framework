"""Robustness verdict model and threshold evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from trading_framework.research.robustness.analytics.diagnostics import (
    StatisticalDiagnosticsAnalytics,
)
from trading_framework.research.robustness.analytics.monte_carlo import MonteCarloAnalytics
from trading_framework.research.robustness.analytics.parameter_sweep import ParameterSweepAnalytics
from trading_framework.research.robustness.analytics.stress import StressTestAnalytics
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardAnalytics
from trading_framework.research.robustness.verdict_thresholds import VerdictThresholds


class VerdictKind(StrEnum):
    """Robustness validation outcome."""

    PASS = "PASS"
    CONDITIONAL = "CONDITIONAL"
    FAIL = "FAIL"


class GateSeverity(StrEnum):
    """Whether a failed gate blocks validation."""

    HARD = "HARD"
    SOFT = "SOFT"


@dataclass(frozen=True, slots=True)
class VerdictGateResult:
    """Outcome for one evaluated threshold gate."""

    gate_id: str
    passed: bool
    severity: str
    message: str
    observed_value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "gate_id": self.gate_id,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
        }
        if self.observed_value is not None:
            payload["observed_value"] = self.observed_value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VerdictGateResult:
        return cls(
            gate_id=str(payload["gate_id"]),
            passed=bool(payload["passed"]),
            severity=str(payload["severity"]),
            message=str(payload["message"]),
            observed_value=(
                str(payload["observed_value"])
                if payload.get("observed_value") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class RobustnessVerdict:
    """Documented validation verdict for one experiment."""

    experiment_id: str
    verdict: VerdictKind
    summary: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    blocking_issues: tuple[str, ...]
    assumptions_fingerprint: str
    best_ranked_config_id: str | None
    gate_results: tuple[VerdictGateResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "verdict": self.verdict.value,
            "summary": self.summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "blocking_issues": list(self.blocking_issues),
            "assumptions_fingerprint": self.assumptions_fingerprint,
            "best_ranked_config_id": self.best_ranked_config_id,
            "gate_results": [gate.to_dict() for gate in self.gate_results],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RobustnessVerdict:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            verdict=VerdictKind(str(payload["verdict"])),
            summary=str(payload["summary"]),
            strengths=tuple(str(item) for item in payload.get("strengths", [])),
            weaknesses=tuple(str(item) for item in payload.get("weaknesses", [])),
            blocking_issues=tuple(str(item) for item in payload.get("blocking_issues", [])),
            assumptions_fingerprint=str(payload["assumptions_fingerprint"]),
            best_ranked_config_id=(
                str(payload["best_ranked_config_id"])
                if payload.get("best_ranked_config_id") is not None
                else None
            ),
            gate_results=tuple(
                VerdictGateResult.from_dict(gate) for gate in payload.get("gate_results", [])
            ),
        )


@dataclass(frozen=True, slots=True)
class VerdictEvaluationContext:
    """Available analytics inputs for threshold evaluation."""

    parameter_sweep: ParameterSweepAnalytics | None = None
    walk_forward: WalkForwardAnalytics | None = None
    stress: StressTestAnalytics | None = None
    monte_carlo: MonteCarloAnalytics | None = None
    diagnostics: StatisticalDiagnosticsAnalytics | None = None


def evaluate_robustness_verdict(
    *,
    experiment_id: str,
    assumptions_fingerprint: str,
    thresholds: VerdictThresholds | None,
    context: VerdictEvaluationContext,
) -> RobustnessVerdict:
    """Evaluate PASS / CONDITIONAL / FAIL from persisted analytics and thresholds."""
    gate_results = _evaluate_gates(thresholds=thresholds, context=context)
    best_config_id = _best_ranked_config_id(context.parameter_sweep)

    hard_failures = [
        gate
        for gate in gate_results
        if not gate.passed and gate.severity == GateSeverity.HARD.value
    ]
    soft_failures = [
        gate
        for gate in gate_results
        if not gate.passed and gate.severity == GateSeverity.SOFT.value
    ]

    blocking_issues = tuple(gate.message for gate in hard_failures)
    weaknesses = tuple(gate.message for gate in soft_failures)
    strengths = tuple(
        f"{gate.gate_id} gate passed ({gate.observed_value})"
        for gate in gate_results
        if gate.passed and gate.observed_value is not None
    )

    if hard_failures:
        verdict = VerdictKind.FAIL
        summary = f"Experiment {experiment_id} failed {len(hard_failures)} hard validation gate(s)."
    elif soft_failures:
        verdict = VerdictKind.CONDITIONAL
        summary = (
            f"Experiment {experiment_id} passed hard gates but failed "
            f"{len(soft_failures)} soft gate(s)."
        )
    else:
        verdict = VerdictKind.PASS
        summary = f"Experiment {experiment_id} passed all configured validation gates."

    if best_config_id is not None:
        summary = f"{summary} Best grid cell: {best_config_id} (ranking ≠ validation)."

    return RobustnessVerdict(
        experiment_id=experiment_id,
        verdict=verdict,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        blocking_issues=blocking_issues,
        assumptions_fingerprint=assumptions_fingerprint,
        best_ranked_config_id=best_config_id,
        gate_results=tuple(gate_results),
    )


def _evaluate_gates(
    *,
    thresholds: VerdictThresholds | None,
    context: VerdictEvaluationContext,
) -> list[VerdictGateResult]:
    if thresholds is None:
        return []

    gates: list[VerdictGateResult] = []

    if thresholds.min_stitched_oos_net_pnl is not None:
        gates.append(_gate_min_stitched_oos_net_pnl(thresholds, context.walk_forward))
    if thresholds.min_oos_beats_train_ratio is not None:
        gates.append(_gate_min_oos_beats_train_ratio(thresholds, context.diagnostics))
    if thresholds.max_worst_stress_delta_net_pnl is not None:
        gates.append(_gate_max_worst_stress_delta(thresholds, context.stress))
    if thresholds.max_mc_loss_probability is not None:
        gates.append(_gate_max_mc_loss_probability(thresholds, context.monte_carlo))
    if thresholds.max_top_trades_concentration is not None:
        gates.append(_gate_max_top_trades_concentration(thresholds, context.diagnostics))
    if thresholds.fail_on_isolated_optima:
        gates.append(_gate_isolated_optima(context.parameter_sweep))

    return gates


def _gate_min_stitched_oos_net_pnl(
    thresholds: VerdictThresholds,
    walk_forward: WalkForwardAnalytics | None,
) -> VerdictGateResult:
    threshold = thresholds.min_stitched_oos_net_pnl
    assert threshold is not None
    if walk_forward is None:
        return VerdictGateResult(
            gate_id="min_stitched_oos_net_pnl",
            passed=False,
            severity=GateSeverity.HARD.value,
            message="Walk-forward analytics required for stitched OOS net PnL gate",
        )
    oos_net = sum(evaluation.oos_summary.net_pnl for evaluation in walk_forward.fold_evaluations)
    passed = oos_net >= threshold
    return VerdictGateResult(
        gate_id="min_stitched_oos_net_pnl",
        passed=passed,
        severity=GateSeverity.HARD.value,
        message=(
            f"Stitched OOS net PnL {oos_net} meets minimum {threshold}"
            if passed
            else f"Stitched OOS net PnL {oos_net} below minimum {threshold}"
        ),
        observed_value=str(oos_net),
    )


def _gate_min_oos_beats_train_ratio(
    thresholds: VerdictThresholds,
    diagnostics: StatisticalDiagnosticsAnalytics | None,
) -> VerdictGateResult:
    threshold = thresholds.min_oos_beats_train_ratio
    assert threshold is not None
    if diagnostics is None or diagnostics.is_oos_degradation is None:
        return VerdictGateResult(
            gate_id="min_oos_beats_train_ratio",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="IS/OOS degradation analytics required for OOS beat-train ratio gate",
        )
    fold_count = len(diagnostics.is_oos_degradation.fold_rows)
    if fold_count == 0:
        return VerdictGateResult(
            gate_id="min_oos_beats_train_ratio",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="No walk-forward folds available for OOS beat-train ratio gate",
        )
    ratio = Decimal(diagnostics.is_oos_degradation.oos_beats_train_count) / Decimal(fold_count)
    passed = ratio >= threshold
    return VerdictGateResult(
        gate_id="min_oos_beats_train_ratio",
        passed=passed,
        severity=GateSeverity.SOFT.value,
        message=(
            f"OOS beat-train ratio {ratio} meets minimum {threshold}"
            if passed
            else f"OOS beat-train ratio {ratio} below minimum {threshold}"
        ),
        observed_value=str(ratio),
    )


def _gate_max_worst_stress_delta(
    thresholds: VerdictThresholds,
    stress: StressTestAnalytics | None,
) -> VerdictGateResult:
    threshold = thresholds.max_worst_stress_delta_net_pnl
    assert threshold is not None
    if stress is None:
        return VerdictGateResult(
            gate_id="max_worst_stress_delta_net_pnl",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="Stress analytics required for stress delta gate",
        )
    deltas = [
        row.delta_net_pnl
        for row in stress.rows
        if row.delta_net_pnl is not None and row.status == "COMPLETED"
    ]
    if not deltas:
        return VerdictGateResult(
            gate_id="max_worst_stress_delta_net_pnl",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="No completed stress scenarios for stress delta gate",
        )
    worst = min(deltas)
    passed = worst >= threshold
    return VerdictGateResult(
        gate_id="max_worst_stress_delta_net_pnl",
        passed=passed,
        severity=GateSeverity.SOFT.value,
        message=(
            f"Worst stress delta {worst} within floor {threshold}"
            if passed
            else f"Worst stress delta {worst} below floor {threshold}"
        ),
        observed_value=str(worst),
    )


def _gate_max_mc_loss_probability(
    thresholds: VerdictThresholds,
    monte_carlo: MonteCarloAnalytics | None,
) -> VerdictGateResult:
    threshold = thresholds.max_mc_loss_probability
    assert threshold is not None
    if monte_carlo is None or not monte_carlo.tail_probabilities:
        return VerdictGateResult(
            gate_id="max_mc_loss_probability",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="Monte Carlo analytics required for terminal loss probability gate",
        )
    observed = max(
        metrics.probability_terminal_pnl_negative for metrics in monte_carlo.tail_probabilities
    )
    passed = observed <= threshold
    return VerdictGateResult(
        gate_id="max_mc_loss_probability",
        passed=passed,
        severity=GateSeverity.SOFT.value,
        message=(
            f"Max MC terminal loss probability {observed} within limit {threshold}"
            if passed
            else f"Max MC terminal loss probability {observed} exceeds limit {threshold}"
        ),
        observed_value=str(observed),
    )


def _gate_max_top_trades_concentration(
    thresholds: VerdictThresholds,
    diagnostics: StatisticalDiagnosticsAnalytics | None,
) -> VerdictGateResult:
    threshold = thresholds.max_top_trades_concentration
    assert threshold is not None
    if diagnostics is None:
        return VerdictGateResult(
            gate_id="max_top_trades_concentration",
            passed=False,
            severity=GateSeverity.SOFT.value,
            message="Diagnostics analytics required for PnL concentration gate",
        )
    observed = abs(diagnostics.pnl_concentration.top_trades_share)
    passed = observed <= threshold
    return VerdictGateResult(
        gate_id="max_top_trades_concentration",
        passed=passed,
        severity=GateSeverity.SOFT.value,
        message=(
            f"Top-trades concentration {observed} within limit {threshold}"
            if passed
            else f"Top-trades concentration {observed} exceeds limit {threshold}"
        ),
        observed_value=str(observed),
    )


def _gate_isolated_optima(
    parameter_sweep: ParameterSweepAnalytics | None,
) -> VerdictGateResult:
    if parameter_sweep is None:
        return VerdictGateResult(
            gate_id="fail_on_isolated_optima",
            passed=True,
            severity=GateSeverity.HARD.value,
            message="No parameter sweep analytics — isolated optimum gate skipped",
        )
    isolated = [flag for flag in parameter_sweep.isolated_optima if flag.is_isolated_optimum]
    passed = len(isolated) == 0
    return VerdictGateResult(
        gate_id="fail_on_isolated_optima",
        passed=passed,
        severity=GateSeverity.HARD.value,
        message=(
            "No isolated parameter optima detected"
            if passed
            else f"Detected {len(isolated)} isolated parameter optimum flag(s)"
        ),
        observed_value=str(len(isolated)),
    )


def _best_ranked_config_id(
    parameter_sweep: ParameterSweepAnalytics | None,
) -> str | None:
    if parameter_sweep is None or not parameter_sweep.rankings:
        return None
    return parameter_sweep.rankings[0].config_id
