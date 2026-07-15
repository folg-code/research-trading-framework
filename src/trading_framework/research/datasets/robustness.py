"""Robustness experiment persistence — manifest, registry, child-run linkage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    robustness_experiment_analytics_dir,
    robustness_experiment_dir,
    robustness_experiment_folds_dir,
    robustness_experiment_monte_carlo_dir,
    robustness_experiment_stress_dir,
)
from trading_framework.research.robustness.analytics.diagnostics import (
    StatisticalDiagnosticsAnalytics,
)
from trading_framework.research.robustness.analytics.monte_carlo import MonteCarloAnalytics
from trading_framework.research.robustness.analytics.parameter_sweep import ParameterSweepAnalytics
from trading_framework.research.robustness.analytics.stress import StressTestAnalytics
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardAnalytics
from trading_framework.research.robustness.experiment import RobustnessExperimentSpec
from trading_framework.research.robustness.monte_carlo import MonteCarloResults
from trading_framework.research.robustness.stress import StressTestResults
from trading_framework.research.robustness.walk_forward import (
    WalkForwardFoldPlan,
    WalkForwardResults,
)

ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION = "robustness_experiment.v1"


class ExperimentConfigStatus(StrEnum):
    """Execution status for one experiment grid cell."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class RobustnessExperimentManifest:
    """Persisted experiment metadata."""

    experiment_id: str
    schema_version: str
    framework_version: str
    created_at_utc: datetime
    spec: RobustnessExperimentSpec
    simulation_assumptions_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "schema_version": self.schema_version,
            "framework_version": self.framework_version,
            "created_at_utc": self.created_at_utc.isoformat(),
            "simulation_assumptions_fingerprint": self.simulation_assumptions_fingerprint,
            "spec": self.spec.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RobustnessExperimentManifest:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            schema_version=str(payload["schema_version"]),
            framework_version=str(payload["framework_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
            simulation_assumptions_fingerprint=str(payload["simulation_assumptions_fingerprint"]),
            spec=RobustnessExperimentSpec.from_dict(payload["spec"]),
        )


@dataclass(frozen=True, slots=True)
class ExperimentRegistryEntry:
    """One planned or completed config cell in an experiment registry."""

    config_id: str
    config_fingerprint: str
    parameter_overrides: dict[str, str]
    status: ExperimentConfigStatus
    strategy_run_id: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "config_id": self.config_id,
            "config_fingerprint": self.config_fingerprint,
            "parameter_overrides": self.parameter_overrides,
            "status": self.status.value,
        }
        if self.strategy_run_id is not None:
            payload["strategy_run_id"] = self.strategy_run_id
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExperimentRegistryEntry:
        return cls(
            config_id=str(payload["config_id"]),
            config_fingerprint=str(payload["config_fingerprint"]),
            parameter_overrides={
                str(key): str(value) for key, value in payload["parameter_overrides"].items()
            },
            status=ExperimentConfigStatus(str(payload["status"])),
            strategy_run_id=(
                str(payload["strategy_run_id"])
                if payload.get("strategy_run_id") is not None
                else None
            ),
            error_message=(
                str(payload["error_message"]) if payload.get("error_message") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ExperimentRegistry:
    """Resume cursor and completion state for one experiment."""

    experiment_id: str
    entries: tuple[ExperimentRegistryEntry, ...]
    next_pending_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "next_pending_index": self.next_pending_index,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExperimentRegistry:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            next_pending_index=int(payload["next_pending_index"]),
            entries=tuple(ExperimentRegistryEntry.from_dict(entry) for entry in payload["entries"]),
        )


@dataclass(frozen=True, slots=True)
class ChildRunRecord:
    """Append-only linkage between experiment config and Strategy Research run."""

    experiment_id: str
    config_id: str
    config_fingerprint: str
    strategy_run_id: str
    recorded_at_utc: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "config_id": self.config_id,
            "config_fingerprint": self.config_fingerprint,
            "strategy_run_id": self.strategy_run_id,
            "recorded_at_utc": self.recorded_at_utc.isoformat(),
        }


class RobustnessExperimentRepository:
    """Persist and load robustness experiment manifests and registries."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def experiment_dir(self, experiment_id: str) -> Path:
        return robustness_experiment_dir(self._root, experiment_id)

    def write_manifest(self, manifest: RobustnessExperimentManifest) -> None:
        if manifest.schema_version != ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)
        experiment_dir = self.experiment_dir(manifest.experiment_id)
        experiment_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = experiment_dir / "manifest.json"
        if manifest_path.exists():
            msg = f"experiment manifest already exists: {manifest_path}"
            raise FileExistsError(msg)
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )

    def read_manifest(self, experiment_id: str) -> RobustnessExperimentManifest:
        manifest_path = self.experiment_dir(experiment_id) / "manifest.json"
        if not manifest_path.exists():
            msg = f"missing experiment manifest: {manifest_path}"
            raise FileNotFoundError(msg)
        manifest = RobustnessExperimentManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)
        return manifest

    def write_registry(self, registry: ExperimentRegistry) -> None:
        registry_path = self.experiment_dir(registry.experiment_id) / "registry.json"
        registry_path.write_text(
            json.dumps(registry.to_dict(), indent=2),
            encoding="utf-8",
        )

    def read_registry(self, experiment_id: str) -> ExperimentRegistry:
        registry_path = self.experiment_dir(experiment_id) / "registry.json"
        if not registry_path.exists():
            msg = f"missing experiment registry: {registry_path}"
            raise FileNotFoundError(msg)
        return ExperimentRegistry.from_dict(json.loads(registry_path.read_text(encoding="utf-8")))

    def append_child_run(self, record: ChildRunRecord) -> None:
        child_runs_path = self.experiment_dir(record.experiment_id) / "child_runs.jsonl"
        child_runs_path.parent.mkdir(parents=True, exist_ok=True)
        with child_runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), separators=(",", ":")))
            handle.write("\n")

    def read_child_runs(self, experiment_id: str) -> tuple[ChildRunRecord, ...]:
        child_runs_path = self.experiment_dir(experiment_id) / "child_runs.jsonl"
        if not child_runs_path.exists():
            return ()
        records: list[ChildRunRecord] = []
        for line in child_runs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(
                ChildRunRecord(
                    experiment_id=str(payload["experiment_id"]),
                    config_id=str(payload["config_id"]),
                    config_fingerprint=str(payload["config_fingerprint"]),
                    strategy_run_id=str(payload["strategy_run_id"]),
                    recorded_at_utc=datetime.fromisoformat(str(payload["recorded_at_utc"])),
                )
            )
        return tuple(records)

    def manifest_exists(self, experiment_id: str) -> bool:
        return (self.experiment_dir(experiment_id) / "manifest.json").exists()

    def write_parameter_sweep_analytics(self, analytics: ParameterSweepAnalytics) -> None:
        analytics_dir = robustness_experiment_analytics_dir(self._root, analytics.experiment_id)
        analytics_dir.mkdir(parents=True, exist_ok=True)
        analytics_path = analytics_dir / "parameter_sweep.json"
        analytics_path.write_text(
            json.dumps(analytics.to_dict(), indent=2),
            encoding="utf-8",
        )

    def read_parameter_sweep_analytics(self, experiment_id: str) -> ParameterSweepAnalytics:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "parameter_sweep.json"
        )
        if not analytics_path.exists():
            msg = f"missing parameter sweep analytics: {analytics_path}"
            raise FileNotFoundError(msg)
        return ParameterSweepAnalytics.from_dict(
            json.loads(analytics_path.read_text(encoding="utf-8"))
        )

    def parameter_sweep_analytics_exists(self, experiment_id: str) -> bool:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "parameter_sweep.json"
        )
        return analytics_path.exists()

    def write_walk_forward_plan(self, plan: WalkForwardFoldPlan) -> None:
        folds_dir = robustness_experiment_folds_dir(self._root, plan.experiment_id)
        folds_dir.mkdir(parents=True, exist_ok=True)
        plan_path = folds_dir / "plan.json"
        if plan_path.exists():
            msg = f"walk-forward plan already exists: {plan_path}"
            raise FileExistsError(msg)
        plan_path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")

    def read_walk_forward_plan(self, experiment_id: str) -> WalkForwardFoldPlan:
        plan_path = robustness_experiment_folds_dir(self._root, experiment_id) / "plan.json"
        if not plan_path.exists():
            msg = f"missing walk-forward plan: {plan_path}"
            raise FileNotFoundError(msg)
        return WalkForwardFoldPlan.from_dict(json.loads(plan_path.read_text(encoding="utf-8")))

    def write_walk_forward_results(self, results: WalkForwardResults) -> None:
        folds_dir = robustness_experiment_folds_dir(self._root, results.experiment_id)
        folds_dir.mkdir(parents=True, exist_ok=True)
        results_path = folds_dir / "results.json"
        results_path.write_text(json.dumps(results.to_dict(), indent=2), encoding="utf-8")

    def read_walk_forward_results(self, experiment_id: str) -> WalkForwardResults:
        results_path = robustness_experiment_folds_dir(self._root, experiment_id) / "results.json"
        if not results_path.exists():
            msg = f"missing walk-forward results: {results_path}"
            raise FileNotFoundError(msg)
        return WalkForwardResults.from_dict(json.loads(results_path.read_text(encoding="utf-8")))

    def walk_forward_plan_exists(self, experiment_id: str) -> bool:
        plan_path = robustness_experiment_folds_dir(self._root, experiment_id) / "plan.json"
        return plan_path.exists()

    def write_walk_forward_analytics(self, analytics: WalkForwardAnalytics) -> None:
        analytics_dir = robustness_experiment_analytics_dir(self._root, analytics.experiment_id)
        analytics_dir.mkdir(parents=True, exist_ok=True)
        analytics_path = analytics_dir / "walk_forward.json"
        analytics_path.write_text(json.dumps(analytics.to_dict(), indent=2), encoding="utf-8")

    def read_walk_forward_analytics(self, experiment_id: str) -> WalkForwardAnalytics:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "walk_forward.json"
        )
        if not analytics_path.exists():
            msg = f"missing walk-forward analytics: {analytics_path}"
            raise FileNotFoundError(msg)
        return WalkForwardAnalytics.from_dict(
            json.loads(analytics_path.read_text(encoding="utf-8"))
        )

    def write_stress_results(self, results: StressTestResults) -> None:
        stress_dir = robustness_experiment_stress_dir(self._root, results.experiment_id)
        stress_dir.mkdir(parents=True, exist_ok=True)
        results_path = stress_dir / "results.json"
        results_path.write_text(json.dumps(results.to_dict(), indent=2), encoding="utf-8")

    def read_stress_results(self, experiment_id: str) -> StressTestResults:
        results_path = robustness_experiment_stress_dir(self._root, experiment_id) / "results.json"
        if not results_path.exists():
            msg = f"missing stress results: {results_path}"
            raise FileNotFoundError(msg)
        return StressTestResults.from_dict(json.loads(results_path.read_text(encoding="utf-8")))

    def stress_results_exist(self, experiment_id: str) -> bool:
        results_path = robustness_experiment_stress_dir(self._root, experiment_id) / "results.json"
        return results_path.exists()

    def write_stress_analytics(self, analytics: StressTestAnalytics) -> None:
        analytics_dir = robustness_experiment_analytics_dir(self._root, analytics.experiment_id)
        analytics_dir.mkdir(parents=True, exist_ok=True)
        analytics_path = analytics_dir / "stress.json"
        analytics_path.write_text(json.dumps(analytics.to_dict(), indent=2), encoding="utf-8")

    def read_stress_analytics(self, experiment_id: str) -> StressTestAnalytics:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "stress.json"
        )
        if not analytics_path.exists():
            msg = f"missing stress analytics: {analytics_path}"
            raise FileNotFoundError(msg)
        return StressTestAnalytics.from_dict(json.loads(analytics_path.read_text(encoding="utf-8")))

    def write_monte_carlo_results(self, results: MonteCarloResults) -> None:
        monte_carlo_dir = robustness_experiment_monte_carlo_dir(self._root, results.experiment_id)
        monte_carlo_dir.mkdir(parents=True, exist_ok=True)
        results_path = monte_carlo_dir / "results.json"
        results_path.write_text(json.dumps(results.to_dict(), indent=2), encoding="utf-8")

    def read_monte_carlo_results(self, experiment_id: str) -> MonteCarloResults:
        results_path = (
            robustness_experiment_monte_carlo_dir(self._root, experiment_id) / "results.json"
        )
        if not results_path.exists():
            msg = f"missing monte carlo results: {results_path}"
            raise FileNotFoundError(msg)
        return MonteCarloResults.from_dict(json.loads(results_path.read_text(encoding="utf-8")))

    def monte_carlo_results_exist(self, experiment_id: str) -> bool:
        results_path = (
            robustness_experiment_monte_carlo_dir(self._root, experiment_id) / "results.json"
        )
        return results_path.exists()

    def write_monte_carlo_analytics(self, analytics: MonteCarloAnalytics) -> None:
        analytics_dir = robustness_experiment_analytics_dir(self._root, analytics.experiment_id)
        analytics_dir.mkdir(parents=True, exist_ok=True)
        analytics_path = analytics_dir / "monte_carlo.json"
        analytics_path.write_text(json.dumps(analytics.to_dict(), indent=2), encoding="utf-8")

    def read_monte_carlo_analytics(self, experiment_id: str) -> MonteCarloAnalytics:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "monte_carlo.json"
        )
        if not analytics_path.exists():
            msg = f"missing monte carlo analytics: {analytics_path}"
            raise FileNotFoundError(msg)
        return MonteCarloAnalytics.from_dict(json.loads(analytics_path.read_text(encoding="utf-8")))

    def write_diagnostics_analytics(self, analytics: StatisticalDiagnosticsAnalytics) -> None:
        analytics_dir = robustness_experiment_analytics_dir(self._root, analytics.experiment_id)
        analytics_dir.mkdir(parents=True, exist_ok=True)
        analytics_path = analytics_dir / "diagnostics.json"
        analytics_path.write_text(json.dumps(analytics.to_dict(), indent=2), encoding="utf-8")

    def read_diagnostics_analytics(self, experiment_id: str) -> StatisticalDiagnosticsAnalytics:
        analytics_path = (
            robustness_experiment_analytics_dir(self._root, experiment_id) / "diagnostics.json"
        )
        if not analytics_path.exists():
            msg = f"missing diagnostics analytics: {analytics_path}"
            raise FileNotFoundError(msg)
        return StatisticalDiagnosticsAnalytics.from_dict(
            json.loads(analytics_path.read_text(encoding="utf-8"))
        )
