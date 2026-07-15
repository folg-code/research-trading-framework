"""Monte Carlo experiment contracts — trade-level resampling specs and results."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError

DEFAULT_MONTE_CARLO_PATH_COUNT = 500


class MonteCarloMethod(StrEnum):
    """Trade-level Monte Carlo resampling methods."""

    TRADE_SHUFFLE = "TRADE_SHUFFLE"
    TRADE_BOOTSTRAP = "TRADE_BOOTSTRAP"
    BLOCK_BOOTSTRAP = "BLOCK_BOOTSTRAP"


@dataclass(frozen=True, slots=True)
class MonteCarloSpec:
    """Declared Monte Carlo settings for one experiment."""

    methods: tuple[MonteCarloMethod, ...] = (
        MonteCarloMethod.TRADE_SHUFFLE,
        MonteCarloMethod.TRADE_BOOTSTRAP,
        MonteCarloMethod.BLOCK_BOOTSTRAP,
    )
    path_count: int = DEFAULT_MONTE_CARLO_PATH_COUNT
    rng_seed: int = 42
    parameter_overrides: dict[str, str] | None = None
    max_drawdown_threshold: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.methods:
            msg = "monte carlo requires at least one method"
            raise ValidationError(msg)
        if self.path_count <= 0:
            msg = "path_count must be positive"
            raise ValidationError(msg)
        if self.parameter_overrides is None:
            object.__setattr__(self, "parameter_overrides", {})

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "methods": [method.value for method in self.methods],
            "path_count": self.path_count,
            "rng_seed": self.rng_seed,
            "parameter_overrides": self.parameter_overrides,
        }
        if self.max_drawdown_threshold is not None:
            payload["max_drawdown_threshold"] = str(self.max_drawdown_threshold)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloSpec:
        overrides_payload = payload.get("parameter_overrides", {})
        threshold_payload = payload.get("max_drawdown_threshold")
        return cls(
            methods=tuple(MonteCarloMethod(method) for method in payload["methods"]),
            path_count=int(payload["path_count"]),
            rng_seed=int(payload["rng_seed"]),
            parameter_overrides={str(key): str(value) for key, value in overrides_payload.items()},
            max_drawdown_threshold=(
                Decimal(str(threshold_payload)) if threshold_payload is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class MonteCarloPathSummary:
    """Summary metrics for one simulated Monte Carlo path."""

    path_index: int
    method: str
    net_pnl: str
    terminal_equity: str
    max_drawdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_index": self.path_index,
            "method": self.method,
            "net_pnl": self.net_pnl,
            "terminal_equity": self.terminal_equity,
            "max_drawdown": self.max_drawdown,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloPathSummary:
        return cls(
            path_index=int(payload["path_index"]),
            method=str(payload["method"]),
            net_pnl=str(payload["net_pnl"]),
            terminal_equity=str(payload["terminal_equity"]),
            max_drawdown=str(payload["max_drawdown"]),
        )


@dataclass(frozen=True, slots=True)
class MonteCarloPercentilePoint:
    """Percentile equity band at one trade index."""

    trade_index: int
    p5: str
    p50: str
    p95: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_index": self.trade_index,
            "p5": self.p5,
            "p50": self.p50,
            "p95": self.p95,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloPercentilePoint:
        return cls(
            trade_index=int(payload["trade_index"]),
            p5=str(payload["p5"]),
            p50=str(payload["p50"]),
            p95=str(payload["p95"]),
        )


@dataclass(frozen=True, slots=True)
class MonteCarloMethodResult:
    """Persisted Monte Carlo output for one resampling method."""

    method: str
    path_count: int
    path_summaries: tuple[MonteCarloPathSummary, ...]
    percentile_equity: tuple[MonteCarloPercentilePoint, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path_count": self.path_count,
            "path_summaries": [summary.to_dict() for summary in self.path_summaries],
            "percentile_equity": [point.to_dict() for point in self.percentile_equity],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloMethodResult:
        return cls(
            method=str(payload["method"]),
            path_count=int(payload["path_count"]),
            path_summaries=tuple(
                MonteCarloPathSummary.from_dict(summary) for summary in payload["path_summaries"]
            ),
            percentile_equity=tuple(
                MonteCarloPercentilePoint.from_dict(point) for point in payload["percentile_equity"]
            ),
        )


@dataclass(frozen=True, slots=True)
class MonteCarloResults:
    """Persisted Monte Carlo execution state."""

    experiment_id: str
    reference_strategy_run_id: str
    rng_seed: int
    methods: tuple[MonteCarloMethodResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "reference_strategy_run_id": self.reference_strategy_run_id,
            "rng_seed": self.rng_seed,
            "methods": [method.to_dict() for method in self.methods],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MonteCarloResults:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            reference_strategy_run_id=str(payload["reference_strategy_run_id"]),
            rng_seed=int(payload["rng_seed"]),
            methods=tuple(
                MonteCarloMethodResult.from_dict(method) for method in payload["methods"]
            ),
        )
