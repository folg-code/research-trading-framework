"""T019: neural families vs S040 baselines on a synthetic known-signal study.

Synthetic labelled frames only — no NQ. Feedforward must recover the known
signal above RANDOM_PERMUTATION. LSTM trains on windowed features of the same
study; beating feedforward is not required. Noise labels must stay inside the
permutation-baseline spread. Extra ``dl`` is independent of extra ``ml`` /
``ml-trees`` (D-S043-06 / D-S043-17 / D-S043-19).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    ComparePredictiveRunsRequest,
    RunPredictiveResearchRequest,
    compare_predictive_runs,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_dir,
    predictive_research_run_window_accounting_path,
)
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.predictive import (
    EstimatorSpec,
    LeaderboardRowKind,
    MetricSource,
    PredictiveMetricsReport,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    SequenceWindowSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("torch")

pytestmark = [
    pytest.mark.torch,
    pytest.mark.skipif(
        os.getenv("TRADING_FRAMEWORK_RUN_TORCH_TESTS") != "1",
        reason="set TRADING_FRAMEWORK_RUN_TORCH_TESTS=1 to run torch training tests",
    ),
]

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_ROW_COUNT = 300
_SIGNAL_RANK_IC_FLOOR = 0.45
_SIGNAL_VS_PERMUTATION_MARGIN = 0.25
_NOISE_SPEARMAN_BAND = 0.15
_WINDOW_SPEC = SequenceWindowSpec(lookback_bars=4)
_FEEDFORWARD_FAMILY = "torch.feedforward.regressor"
_LSTM_FAMILY = "torch.lstm.regressor"


def _split_spec() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=4,
        test_span=Timeframe("40m"),
        embargo_span=Timeframe("5m"),
        min_train_rows=40,
    )


def _series_labelled_rows(*, mode: str, seed: int = 42) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(_ROW_COUNT)]
    signal_x = rng.normal(0.0, 1.0, _ROW_COUNT)
    noise_a = rng.normal(0.0, 1.0, _ROW_COUNT)
    noise_b = rng.normal(0.0, 1.0, _ROW_COUNT)
    residual = rng.normal(0.0, 0.25, _ROW_COUNT)
    if mode == "known_signal":
        labels = 2.0 * signal_x + residual
        returns = labels
    elif mode == "noise":
        labels = rng.normal(0.0, 1.0, _ROW_COUNT)
        returns = rng.normal(0.0, 1.0, _ROW_COUNT)
    else:
        msg = f"unknown labelled-row mode: {mode}"
        raise ValueError(msg)
    return pl.DataFrame(
        {
            "entity_id": ["ES.c.0"] * _ROW_COUNT,
            "horizon_bars": [5] * _ROW_COUNT,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "signal_x": signal_x.tolist(),
            "noise_a": noise_a.tolist(),
            "noise_b": noise_b.tolist(),
            "label": labels.tolist(),
            "forward_return": returns.tolist(),
            "outcome_status": ["COMPLETE"] * _ROW_COUNT,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC_US,
            "available_at": _UTC_US,
            "label_end_at": _UTC_US,
            "signal_x": pl.Float64(),
            "noise_a": pl.Float64(),
            "noise_b": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _write_dataset(
    storage_root: Path,
    rows: pl.DataFrame,
    *,
    dataset_id: str,
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(rows, _split_spec())
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "known_signal_fixture",
                    "label": {"kind": "REGRESSION", "horizon": "5m"},
                },
                definition_hash="b" * 64,
                dataset_fingerprint=dataset_id + ("d" * 48),
                source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
                exclusion_counts={
                    "candidate_rows": _ROW_COUNT,
                    "labelled_rows": _ROW_COUNT,
                    "incomplete_horizon": 0,
                    "insufficient_data": 0,
                    "null_features": 0,
                },
                fold_summary=fold_summary_from_features(features),
                framework_version=framework_version,
                created_at_utc=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            ),
            features=features,
            folds=resolve_fold_boundaries(features),
        )
    )


def _feedforward_spec() -> EstimatorSpec:
    return EstimatorSpec(
        family=_FEEDFORWARD_FAMILY,
        hyperparameters={
            "hidden_sizes": [8],
            "max_epochs": 12,
            "batch_size": 16,
            "patience": 4,
        },
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _lstm_spec() -> EstimatorSpec:
    return EstimatorSpec(
        family=_LSTM_FAMILY,
        hyperparameters={
            "hidden_size": 8,
            "num_layers": 1,
            "max_epochs": 12,
            "batch_size": 16,
            "patience": 4,
        },
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _run(
    storage_root: Path,
    dataset_ref: PredictiveDatasetRef,
    spec: EstimatorSpec,
    *,
    window_spec: SequenceWindowSpec | None = None,
) -> tuple[str, PredictiveMetricsReport]:
    result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
            window_spec=window_spec,
        )
    )
    return result.run_id, result.metrics


def _metric_value(value: float | None, *, missing: float) -> float:
    if value is None:
        return missing
    return float(value)


def _statistical(
    report: PredictiveMetricsReport,
    source: str,
    field: str,
    *,
    missing: float,
) -> float:
    return _metric_value(getattr(report.pooled[source].statistical, field), missing=missing)


def _fold_statistical(
    report: PredictiveMetricsReport,
    source: str,
    field: str,
    *,
    missing: float,
) -> tuple[float, ...]:
    return tuple(
        _metric_value(getattr(sources[source].statistical, field), missing=missing)
        for sources in report.folds.values()
    )


def _assert_within_permutation_spread(
    report: PredictiveMetricsReport,
    field: str,
    *,
    band: float,
    missing: float,
) -> None:
    model_pooled = _statistical(report, MetricSource.MODEL.value, field, missing=missing)
    perm_pooled = _statistical(
        report, MetricSource.RANDOM_PERMUTATION.value, field, missing=missing
    )
    perm_folds = _fold_statistical(
        report, MetricSource.RANDOM_PERMUTATION.value, field, missing=missing
    )
    spread_low = min((*perm_folds, perm_pooled)) - band
    spread_high = max((*perm_folds, perm_pooled)) + band
    assert spread_low <= model_pooled <= spread_high


def test_neural_families_recover_known_signal_and_share_a_leaderboard(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _series_labelled_rows(mode="known_signal"),
        dataset_id="neuralknownsign01",
    )
    feedforward_id, feedforward_report = _run(storage_root, dataset_ref, _feedforward_spec())
    lstm_id, lstm_report = _run(storage_root, dataset_ref, _lstm_spec(), window_spec=_WINDOW_SPEC)

    feedforward_ic = _statistical(
        feedforward_report, MetricSource.MODEL.value, "spearman_ic", missing=0.0
    )
    feedforward_perm = _statistical(
        feedforward_report, MetricSource.RANDOM_PERMUTATION.value, "spearman_ic", missing=0.0
    )
    assert feedforward_ic > _SIGNAL_RANK_IC_FLOOR
    assert feedforward_ic > feedforward_perm + _SIGNAL_VS_PERMUTATION_MARGIN

    lstm_ic = _statistical(lstm_report, MetricSource.MODEL.value, "spearman_ic", missing=0.0)
    assert np.isfinite(lstm_ic)
    accounting_path = predictive_research_run_window_accounting_path(storage_root, lstm_id)
    assert accounting_path.exists()

    board = compare_predictive_runs(
        ComparePredictiveRunsRequest(
            run_dirs=tuple(
                predictive_research_run_dir(storage_root, run_id)
                for run_id in (feedforward_id, lstm_id)
            )
        )
    )
    estimator_families = {
        row.family for row in board.leaderboard.rows if row.kind is LeaderboardRowKind.ESTIMATOR
    }
    baseline_sources = {
        row.source for row in board.leaderboard.rows if row.kind is LeaderboardRowKind.BASELINE
    }
    assert estimator_families == {_FEEDFORWARD_FAMILY, _LSTM_FAMILY}
    assert MetricSource.CONSTANT_MEAN.value in baseline_sources
    assert MetricSource.RANDOM_PERMUTATION.value in baseline_sources
    assert board.leaderboard.dataset_fingerprint == "neuralknownsign01" + ("d" * 48)


def test_neural_families_on_noise_labels_stay_within_permutation_spread(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _series_labelled_rows(mode="noise"),
        dataset_id="neuralnoiselab001",
    )
    _run_id, feedforward_report = _run(storage_root, dataset_ref, _feedforward_spec())
    _lstm_id, lstm_report = _run(storage_root, dataset_ref, _lstm_spec(), window_spec=_WINDOW_SPEC)
    _assert_within_permutation_spread(
        feedforward_report, "spearman_ic", band=_NOISE_SPEARMAN_BAND, missing=0.0
    )
    _assert_within_permutation_spread(
        lstm_report, "spearman_ic", band=_NOISE_SPEARMAN_BAND, missing=0.0
    )
