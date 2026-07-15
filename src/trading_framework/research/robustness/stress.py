"""Stress testing scenario contracts and assumption transforms."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition


class StressScenarioMode(StrEnum):
    """How one stress scenario is executed."""

    RERUN = "RERUN"
    POST_PROCESS = "POST_PROCESS"


@dataclass(frozen=True, slots=True)
class StressScenarioSpec:
    """One versioned stress scenario declaration."""

    scenario_id: str
    commission_multiplier: Decimal = Decimal("1")
    slippage_multiplier: Decimal = Decimal("1")
    entry_delay_bars: int = 0
    exit_delay_bars: int = 0
    remove_top_n_trades: int = 0
    remove_top_n_days: int = 0

    def __post_init__(self) -> None:
        normalized_id = self.scenario_id.strip()
        if not normalized_id:
            msg = "scenario_id must be non-empty"
            raise ValidationError(msg)
        object.__setattr__(self, "scenario_id", normalized_id)
        _validate_multiplier(self.commission_multiplier, field_name="commission_multiplier")
        _validate_multiplier(self.slippage_multiplier, field_name="slippage_multiplier")
        if self.entry_delay_bars < 0:
            msg = "entry_delay_bars must be >= 0"
            raise ValidationError(msg)
        if self.exit_delay_bars < 0:
            msg = "exit_delay_bars must be >= 0"
            raise ValidationError(msg)
        if self.remove_top_n_trades < 0:
            msg = "remove_top_n_trades must be >= 0"
            raise ValidationError(msg)
        if self.remove_top_n_days < 0:
            msg = "remove_top_n_days must be >= 0"
            raise ValidationError(msg)
        validate_stress_scenario_spec(self)

    def mode(self) -> StressScenarioMode:
        if self.remove_top_n_trades > 0 or self.remove_top_n_days > 0:
            return StressScenarioMode.POST_PROCESS
        return StressScenarioMode.RERUN

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "commission_multiplier": str(self.commission_multiplier),
            "slippage_multiplier": str(self.slippage_multiplier),
            "entry_delay_bars": self.entry_delay_bars,
            "exit_delay_bars": self.exit_delay_bars,
            "remove_top_n_trades": self.remove_top_n_trades,
            "remove_top_n_days": self.remove_top_n_days,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StressScenarioSpec:
        return cls(
            scenario_id=str(payload["scenario_id"]),
            commission_multiplier=Decimal(str(payload.get("commission_multiplier", "1"))),
            slippage_multiplier=Decimal(str(payload.get("slippage_multiplier", "1"))),
            entry_delay_bars=int(payload.get("entry_delay_bars", 0)),
            exit_delay_bars=int(payload.get("exit_delay_bars", 0)),
            remove_top_n_trades=int(payload.get("remove_top_n_trades", 0)),
            remove_top_n_days=int(payload.get("remove_top_n_days", 0)),
        )


@dataclass(frozen=True, slots=True)
class StressTestSpec:
    """Declared stress scenarios for one experiment."""

    scenarios: tuple[StressScenarioSpec, ...]
    parameter_overrides: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.scenarios:
            msg = "stress test requires at least one scenario"
            raise ValidationError(msg)
        scenario_ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(set(scenario_ids)) != len(scenario_ids):
            msg = "stress scenario_id values must be unique"
            raise ValidationError(msg)
        if self.parameter_overrides is None:
            object.__setattr__(self, "parameter_overrides", {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "parameter_overrides": self.parameter_overrides,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StressTestSpec:
        overrides_payload = payload.get("parameter_overrides", {})
        return cls(
            scenarios=tuple(
                StressScenarioSpec.from_dict(scenario) for scenario in payload["scenarios"]
            ),
            parameter_overrides={str(key): str(value) for key, value in overrides_payload.items()},
        )


@dataclass(frozen=True, slots=True)
class StressScenarioResult:
    """Execution outcome for one stress scenario."""

    scenario_id: str
    scenario_fingerprint: str
    mode: str
    status: str
    strategy_run_id: str | None = None
    net_pnl: str | None = None
    trade_count: int | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "scenario_fingerprint": self.scenario_fingerprint,
            "mode": self.mode,
            "status": self.status,
        }
        if self.strategy_run_id is not None:
            payload["strategy_run_id"] = self.strategy_run_id
        if self.net_pnl is not None:
            payload["net_pnl"] = self.net_pnl
        if self.trade_count is not None:
            payload["trade_count"] = self.trade_count
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StressScenarioResult:
        return cls(
            scenario_id=str(payload["scenario_id"]),
            scenario_fingerprint=str(payload["scenario_fingerprint"]),
            mode=str(payload["mode"]),
            status=str(payload["status"]),
            strategy_run_id=(
                str(payload["strategy_run_id"])
                if payload.get("strategy_run_id") is not None
                else None
            ),
            net_pnl=str(payload["net_pnl"]) if payload.get("net_pnl") is not None else None,
            trade_count=(
                int(payload["trade_count"]) if payload.get("trade_count") is not None else None
            ),
            error_message=(
                str(payload["error_message"]) if payload.get("error_message") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class StressTestResults:
    """Persisted stress execution state."""

    experiment_id: str
    baseline_strategy_run_id: str
    scenarios: tuple[StressScenarioResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "baseline_strategy_run_id": self.baseline_strategy_run_id,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StressTestResults:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            baseline_strategy_run_id=str(payload["baseline_strategy_run_id"]),
            scenarios=tuple(
                StressScenarioResult.from_dict(scenario) for scenario in payload["scenarios"]
            ),
        )


def validate_stress_scenario_spec(spec: StressScenarioSpec) -> None:
    """Validate one stress scenario has exactly one active mechanism."""
    rerun_active = (
        spec.commission_multiplier != Decimal("1")
        or spec.slippage_multiplier != Decimal("1")
        or spec.entry_delay_bars > 0
        or spec.exit_delay_bars > 0
    )
    post_active = spec.remove_top_n_trades > 0 or spec.remove_top_n_days > 0
    if not rerun_active and not post_active:
        msg = f"scenario {spec.scenario_id!r} must declare at least one stress dimension"
        raise ValidationError(msg)
    if rerun_active and post_active:
        msg = f"scenario {spec.scenario_id!r} cannot combine rerun and post-process dimensions"
        raise ValidationError(msg)
    if spec.remove_top_n_trades > 0 and spec.remove_top_n_days > 0:
        msg = f"scenario {spec.scenario_id!r} cannot remove both trades and days"
        raise ValidationError(msg)


def scenario_fingerprint(spec: StressScenarioSpec) -> str:
    """Stable fingerprint for one stress scenario."""
    payload = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def apply_stress_assumptions(
    baseline: SimulationAssumptions,
    scenario: StressScenarioSpec,
) -> SimulationAssumptions:
    """Derive stressed simulation assumptions from baseline and scenario multipliers."""
    return SimulationAssumptions(
        fill_policy_entry=baseline.fill_policy_entry,
        fill_policy_exit=baseline.fill_policy_exit,
        slippage_bps=baseline.slippage_bps * scenario.slippage_multiplier,
        commission_per_side=baseline.commission_per_side * scenario.commission_multiplier,
        initial_capital=baseline.initial_capital,
    )


def apply_stress_strategy_model(
    strategy_model: StrategyModelDefinition,
    scenario: StressScenarioSpec,
) -> StrategyModelDefinition:
    """Derive stressed strategy model with delay approximated via extra hold bars."""
    extra_bars = scenario.entry_delay_bars + scenario.exit_delay_bars
    if extra_bars == 0:
        return strategy_model
    exit_model = strategy_model.exit_model
    if not isinstance(exit_model, FixedBarsExitModel):
        msg = "stress delay requires FixedBarsExitModel"
        raise ValidationError(msg)
    return StrategyModelDefinition(
        strategy_model_id=strategy_model.strategy_model_id,
        market_model=strategy_model.market_model,
        signal_model=strategy_model.signal_model,
        exit_model=FixedBarsExitModel(exit_after_bars=exit_model.exit_after_bars + extra_bars),
        risk_model=strategy_model.risk_model,
    )


def _validate_multiplier(value: Decimal, *, field_name: str) -> None:
    if not value.is_finite() or value < 0:
        msg = f"{field_name} must be a non-negative finite decimal"
        raise ValidationError(msg)
