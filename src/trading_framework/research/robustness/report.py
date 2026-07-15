"""Robustness report view model — bundled analytics for HTML rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trading_framework.research.robustness.analytics.diagnostics import (
    StatisticalDiagnosticsAnalytics,
)
from trading_framework.research.robustness.analytics.monte_carlo import MonteCarloAnalytics
from trading_framework.research.robustness.analytics.parameter_sweep import ParameterSweepAnalytics
from trading_framework.research.robustness.analytics.stress import StressTestAnalytics
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardAnalytics
from trading_framework.research.robustness.verdict import RobustnessVerdict
from trading_framework.research.robustness.verdict_thresholds import VerdictThresholds


@dataclass(frozen=True, slots=True)
class RobustnessReportViewModel:
    """Presentation bundle for one analyzed robustness experiment."""

    experiment_id: str
    kinds: tuple[str, ...]
    dataset_ref: str
    strategy_template_id: str
    timeframe: str
    framework_version: str
    simulation_assumptions_fingerprint: str
    verdict: RobustnessVerdict
    verdict_thresholds: VerdictThresholds | None
    parameter_sweep: ParameterSweepAnalytics | None
    walk_forward: WalkForwardAnalytics | None
    stress: StressTestAnalytics | None
    monte_carlo: MonteCarloAnalytics | None
    diagnostics: StatisticalDiagnosticsAnalytics | None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "kinds": list(self.kinds),
            "dataset_ref": self.dataset_ref,
            "strategy_template_id": self.strategy_template_id,
            "timeframe": self.timeframe,
            "framework_version": self.framework_version,
            "simulation_assumptions_fingerprint": self.simulation_assumptions_fingerprint,
            "verdict": self.verdict.to_dict(),
        }
        if self.verdict_thresholds is not None:
            payload["verdict_thresholds"] = self.verdict_thresholds.to_dict()
        if self.parameter_sweep is not None:
            payload["parameter_sweep"] = self.parameter_sweep.to_dict()
        if self.walk_forward is not None:
            payload["walk_forward"] = self.walk_forward.to_dict()
        if self.stress is not None:
            payload["stress"] = self.stress.to_dict()
        if self.monte_carlo is not None:
            payload["monte_carlo"] = self.monte_carlo.to_dict()
        if self.diagnostics is not None:
            payload["diagnostics"] = self.diagnostics.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RobustnessReportViewModel:
        thresholds_payload = payload.get("verdict_thresholds")
        sweep_payload = payload.get("parameter_sweep")
        walk_forward_payload = payload.get("walk_forward")
        stress_payload = payload.get("stress")
        monte_carlo_payload = payload.get("monte_carlo")
        diagnostics_payload = payload.get("diagnostics")
        return cls(
            experiment_id=str(payload["experiment_id"]),
            kinds=tuple(str(kind) for kind in payload["kinds"]),
            dataset_ref=str(payload["dataset_ref"]),
            strategy_template_id=str(payload["strategy_template_id"]),
            timeframe=str(payload["timeframe"]),
            framework_version=str(payload["framework_version"]),
            simulation_assumptions_fingerprint=str(payload["simulation_assumptions_fingerprint"]),
            verdict=RobustnessVerdict.from_dict(payload["verdict"]),
            verdict_thresholds=(
                VerdictThresholds.from_dict(thresholds_payload)
                if thresholds_payload is not None
                else None
            ),
            parameter_sweep=(
                ParameterSweepAnalytics.from_dict(sweep_payload)
                if sweep_payload is not None
                else None
            ),
            walk_forward=(
                WalkForwardAnalytics.from_dict(walk_forward_payload)
                if walk_forward_payload is not None
                else None
            ),
            stress=(
                StressTestAnalytics.from_dict(stress_payload)
                if stress_payload is not None
                else None
            ),
            monte_carlo=(
                MonteCarloAnalytics.from_dict(monte_carlo_payload)
                if monte_carlo_payload is not None
                else None
            ),
            diagnostics=(
                StatisticalDiagnosticsAnalytics.from_dict(diagnostics_payload)
                if diagnostics_payload is not None
                else None
            ),
        )


def build_robustness_report_view_model(
    *,
    experiment_id: str,
    kinds: tuple[str, ...],
    dataset_ref: str,
    strategy_template_id: str,
    timeframe: str,
    framework_version: str,
    simulation_assumptions_fingerprint: str,
    verdict: RobustnessVerdict,
    verdict_thresholds: VerdictThresholds | None,
    parameter_sweep: ParameterSweepAnalytics | None = None,
    walk_forward: WalkForwardAnalytics | None = None,
    stress: StressTestAnalytics | None = None,
    monte_carlo: MonteCarloAnalytics | None = None,
    diagnostics: StatisticalDiagnosticsAnalytics | None = None,
) -> RobustnessReportViewModel:
    """Bundle analyzed artifacts into one report view model."""
    return RobustnessReportViewModel(
        experiment_id=experiment_id,
        kinds=kinds,
        dataset_ref=dataset_ref,
        strategy_template_id=strategy_template_id,
        timeframe=timeframe,
        framework_version=framework_version,
        simulation_assumptions_fingerprint=simulation_assumptions_fingerprint,
        verdict=verdict,
        verdict_thresholds=verdict_thresholds,
        parameter_sweep=parameter_sweep,
        walk_forward=walk_forward,
        stress=stress,
        monte_carlo=monte_carlo,
        diagnostics=diagnostics,
    )
