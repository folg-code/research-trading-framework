"""Unit tests for robustness experiment persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.research.datasets.robustness import (
    ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
    ChildRunRecord,
    ExperimentConfigStatus,
    ExperimentRegistry,
    ExperimentRegistryEntry,
    RobustnessExperimentManifest,
    RobustnessExperimentRepository,
)
from trading_framework.research.robustness.experiment import (
    ParameterSweepAxis,
    ParameterSweepSpec,
    RobustnessExperimentSpec,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.strategy.canonical_examples import CANONICAL_STRATEGY_MODEL_ID


def _manifest(experiment_id: str = "exp-repo-test") -> RobustnessExperimentManifest:
    spec = RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(RobustnessExperimentKind.PARAMETER_SWEEP,),
        dataset_ref="ES.c.0/ohlcv/1m/csv/unit",
        timeframe="1m",
        requested_range_start=datetime(2024, 6, 3, 14, 30, tzinfo=UTC),
        requested_range_end=datetime(2024, 6, 3, 20, 0, tzinfo=UTC),
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        parameter_sweep=ParameterSweepSpec(
            axes=(ParameterSweepAxis(name="exit_after_bars", values=("5",)),)
        ),
    )
    return RobustnessExperimentManifest(
        experiment_id=experiment_id,
        schema_version=ROBUSTNESS_EXPERIMENT_SCHEMA_VERSION,
        framework_version="0.0.0-test",
        created_at_utc=datetime(2024, 6, 3, 12, 0, tzinfo=UTC),
        spec=spec,
        simulation_assumptions_fingerprint="abc123",
    )


def test_robustness_repository_manifest_registry_roundtrip(tmp_path: Path) -> None:
    repo = RobustnessExperimentRepository(tmp_path)
    manifest = _manifest()
    repo.write_manifest(manifest)
    registry = ExperimentRegistry(
        experiment_id=manifest.experiment_id,
        entries=(
            ExperimentRegistryEntry(
                config_id="cell_0000_abcd",
                config_fingerprint="abcd",
                parameter_overrides={"exit_after_bars": "5"},
                status=ExperimentConfigStatus.PENDING,
            ),
        ),
        next_pending_index=0,
    )
    repo.write_registry(registry)

    restored_manifest = repo.read_manifest(manifest.experiment_id)
    restored_registry = repo.read_registry(manifest.experiment_id)

    assert restored_manifest.spec.experiment_id == manifest.experiment_id
    assert restored_registry.entries[0].status is ExperimentConfigStatus.PENDING


def test_robustness_repository_append_child_runs(tmp_path: Path) -> None:
    repo = RobustnessExperimentRepository(tmp_path)
    manifest = _manifest()
    repo.write_manifest(manifest)
    record = ChildRunRecord(
        experiment_id=manifest.experiment_id,
        config_id="cell_0000_abcd",
        config_fingerprint="abcd",
        strategy_run_id="run123",
        recorded_at_utc=datetime(2024, 6, 3, 13, 0, tzinfo=UTC),
    )
    repo.append_child_run(record)
    repo.append_child_run(record)

    child_runs = repo.read_child_runs(manifest.experiment_id)
    assert len(child_runs) == 2
    assert child_runs[0].strategy_run_id == "run123"
