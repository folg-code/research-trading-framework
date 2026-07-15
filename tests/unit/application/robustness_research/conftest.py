"""Shared helpers for robustness research application tests."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.robustness.diagnostics import StatisticalDiagnosticsSpec
from trading_framework.research.robustness.experiment import (
    ParameterSweepAxis,
    ParameterSweepSpec,
    RobustnessExperimentSpec,
)
from trading_framework.research.robustness.kinds import RobustnessExperimentKind
from trading_framework.research.robustness.monte_carlo import MonteCarloSpec
from trading_framework.research.robustness.stress import (
    StressScenarioSpec,
    StressTestSpec,
)
from trading_framework.research.robustness.walk_forward import (
    WalkForwardSpec,
    WalkForwardWindowMode,
)
from trading_framework.strategy.canonical_examples import CANONICAL_STRATEGY_MODEL_ID
from trading_framework.time.models.timeframe import Timeframe


def write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="unit-robustness-experiment",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return result.dataset_ref


def build_parameter_sweep_spec(
    *,
    experiment_id: str,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
) -> RobustnessExperimentSpec:
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(RobustnessExperimentKind.PARAMETER_SWEEP,),
        dataset_ref=str(dataset_ref),
        timeframe="1m",
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        evaluation_timeframe="1m",
        parameter_sweep=ParameterSweepSpec(
            axes=(ParameterSweepAxis(name="exit_after_bars", values=("5", "10")),)
        ),
    )


def build_stress_test_spec(
    *,
    experiment_id: str,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
) -> RobustnessExperimentSpec:
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(RobustnessExperimentKind.STRESS_TEST,),
        dataset_ref=str(dataset_ref),
        timeframe="1m",
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        evaluation_timeframe="1m",
        stress_test=StressTestSpec(
            scenarios=(
                StressScenarioSpec(
                    scenario_id="double_commission",
                    commission_multiplier=Decimal("2"),
                ),
                StressScenarioSpec(
                    scenario_id="remove_top_trade",
                    remove_top_n_trades=1,
                ),
            ),
            parameter_overrides={"exit_after_bars": "5"},
        ),
    )


def build_monte_carlo_diagnostics_spec(
    *,
    experiment_id: str,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
) -> RobustnessExperimentSpec:
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(
            RobustnessExperimentKind.MONTE_CARLO,
            RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS,
        ),
        dataset_ref=str(dataset_ref),
        timeframe="1m",
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        evaluation_timeframe="1m",
        monte_carlo=MonteCarloSpec(
            path_count=50,
            rng_seed=7,
            parameter_overrides={"exit_after_bars": "5"},
            max_drawdown_threshold=Decimal("-500"),
        ),
        statistical_diagnostics=StatisticalDiagnosticsSpec(
            top_k_trades=2,
            top_k_days=2,
            parameter_overrides={"exit_after_bars": "5"},
        ),
    )


def build_walk_forward_spec(
    *,
    experiment_id: str,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
) -> RobustnessExperimentSpec:
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(RobustnessExperimentKind.WALK_FORWARD,),
        dataset_ref=str(dataset_ref),
        timeframe="1m",
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        evaluation_timeframe="1m",
        parameter_sweep=ParameterSweepSpec(
            axes=(ParameterSweepAxis(name="exit_after_bars", values=("5", "10")),)
        ),
        walk_forward=WalkForwardSpec(
            window_mode=WalkForwardWindowMode.ROLLING,
            train_duration_seconds=4 * 3600,
            oos_duration_seconds=3600,
            step_duration_seconds=2 * 3600,
        ),
    )
