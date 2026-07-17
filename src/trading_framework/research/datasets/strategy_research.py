"""Strategy Research run envelope — manifest, schema validation, persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    strategy_research_run_dir,
    strategy_research_summary_metrics_path,
)
from trading_framework.research.simulation.facts import (
    empty_equity_points_dataframe,
    empty_simulated_trades_dataframe,
)

STRATEGY_RESEARCH_SCHEMA_VERSION = "strategy_research.v1"


@dataclass(frozen=True, slots=True)
class StrategyResearchRunRef:
    """Logical reference to one persisted Strategy Research run."""

    run_id: str

    def __post_init__(self) -> None:
        normalized = self.run_id.strip()
        if not normalized:
            msg = "run_id must be non-empty"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class StrategyResearchRunManifest:
    """Run-level metadata for one Strategy Research envelope."""

    run_id: str
    schema_version: str
    framework_version: str
    created_at_utc: datetime
    source_dataset_ref: str
    evaluation_timeframe: str
    strategy_model_id: str
    market_model_id: str
    signal_model_id: str
    exit_model_id: str
    risk_model_id: str
    simulation_assumptions_fingerprint: str
    experiment_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "framework_version": self.framework_version,
            "created_at_utc": self.created_at_utc.isoformat(),
            "source_dataset_ref": self.source_dataset_ref,
            "evaluation_timeframe": self.evaluation_timeframe,
            "strategy_model_id": self.strategy_model_id,
            "market_model_id": self.market_model_id,
            "signal_model_id": self.signal_model_id,
            "exit_model_id": self.exit_model_id,
            "risk_model_id": self.risk_model_id,
            "simulation_assumptions_fingerprint": self.simulation_assumptions_fingerprint,
        }
        if self.experiment_id is not None:
            payload["experiment_id"] = self.experiment_id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StrategyResearchRunManifest:
        return cls(
            run_id=str(payload["run_id"]),
            schema_version=str(payload["schema_version"]),
            framework_version=str(payload["framework_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
            source_dataset_ref=str(payload["source_dataset_ref"]),
            evaluation_timeframe=str(payload["evaluation_timeframe"]),
            strategy_model_id=str(payload["strategy_model_id"]),
            market_model_id=str(payload["market_model_id"]),
            signal_model_id=str(payload["signal_model_id"]),
            exit_model_id=str(payload["exit_model_id"]),
            risk_model_id=str(payload["risk_model_id"]),
            simulation_assumptions_fingerprint=str(payload["simulation_assumptions_fingerprint"]),
            experiment_id=(
                str(payload["experiment_id"]) if payload.get("experiment_id") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class StrategyResearchRunEnvelope:
    """In-memory Strategy Research run envelope."""

    manifest: StrategyResearchRunManifest
    trades: pl.DataFrame
    equity: pl.DataFrame


def derive_strategy_run_id(
    *,
    strategy_model_id: str,
    market_model_id: str,
    signal_model_id: str,
    exit_model_id: str,
    exit_after_bars: int,
    risk_model_id: str,
    position_quantity: str,
    source_dataset_ref: str,
    evaluation_timeframe: str,
    requested_range_start: datetime,
    requested_range_end: datetime,
    framework_version: str,
    simulation_assumptions_fingerprint: str,
) -> str:
    """Deterministic run identity including strategy models and simulation assumptions."""
    payload = "|".join(
        [
            "strategy_research",
            strategy_model_id,
            market_model_id,
            signal_model_id,
            exit_model_id,
            str(exit_after_bars),
            risk_model_id,
            position_quantity,
            source_dataset_ref,
            evaluation_timeframe,
            requested_range_start.isoformat(),
            requested_range_end.isoformat(),
            framework_version,
            simulation_assumptions_fingerprint,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def validate_trades_dataframe(frame: pl.DataFrame) -> None:
    expected = empty_simulated_trades_dataframe()
    if frame.columns != expected.columns:
        msg = f"trades columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


def validate_equity_dataframe(frame: pl.DataFrame) -> None:
    expected = empty_equity_points_dataframe()
    if frame.columns != expected.columns:
        msg = f"equity columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


class StrategyResearchDatasetRepository:
    """Persist and load Strategy Research run envelopes."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(self, envelope: StrategyResearchRunEnvelope) -> StrategyResearchRunRef:
        validate_trades_dataframe(envelope.trades)
        validate_equity_dataframe(envelope.equity)
        if not envelope.manifest.run_id.strip():
            msg = "manifest run_id must be non-empty"
            raise ValidationError(msg)
        if envelope.manifest.schema_version != STRATEGY_RESEARCH_SCHEMA_VERSION:
            msg = f"unsupported schema version: {envelope.manifest.schema_version}"
            raise ValidationError(msg)

        run_dir = strategy_research_run_dir(self._root, envelope.manifest.run_id)
        if run_dir.exists():
            msg = f"run directory already exists: {run_dir}"
            raise FileExistsError(msg)

        run_dir.mkdir(parents=True, exist_ok=False)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(envelope.manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        envelope.trades.write_parquet(run_dir / "trades.parquet")
        envelope.equity.write_parquet(run_dir / "equity.parquet")
        return StrategyResearchRunRef(run_id=envelope.manifest.run_id)

    def write_summary_metrics(self, run_id: str, metrics: pl.DataFrame) -> Path:
        """Persist dashboard KPI metrics under ``analytics/summary_metrics.parquet``."""
        run_dir = strategy_research_run_dir(self._root, run_id)
        if not run_dir.exists():
            msg = f"run directory not found: {run_dir}"
            raise FileNotFoundError(msg)
        if metrics.height < 1:
            msg = "summary metrics frame must contain at least one row"
            raise ValidationError(msg)
        path = strategy_research_summary_metrics_path(self._root, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        metrics.write_parquet(path)
        return path

    def read(self, ref: StrategyResearchRunRef) -> StrategyResearchRunEnvelope:
        run_dir = strategy_research_run_dir(self._root, ref.run_id)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            msg = f"missing manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        manifest = StrategyResearchRunManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != STRATEGY_RESEARCH_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        trades = pl.read_parquet(run_dir / "trades.parquet")
        equity = pl.read_parquet(run_dir / "equity.parquet")
        validate_trades_dataframe(trades)
        validate_equity_dataframe(equity)
        return StrategyResearchRunEnvelope(manifest=manifest, trades=trades, equity=equity)
