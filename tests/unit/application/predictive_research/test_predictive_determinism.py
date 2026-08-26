"""T020: same spec + dataset fingerprint yields identical predictions and run_id.

Does not pin process-wide thread-pool env vars; the sklearn adapter already
sets n_jobs=1 where the estimator accepts it (D-S040-16).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    AnalyzePredictiveRunRequest,
    RunPredictiveResearchRequest,
    analyze_predictive_run,
    run_predictive_research,
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
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_THREAD_POOL_ENV = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "LOKY_MAX_CPU_COUNT",
)


def _labelled_rows(*, binary: bool = False) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    count = 40
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    returns = [0.01 + (index * 0.001) for index in range(count)]
    labels = [1.0 if index % 2 else 0.0 for index in range(count)] if binary else returns
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [float(index) for index in range(count)],
            "label": labels,
            "forward_return": returns,
            "outcome_status": ["COMPLETE"] * count,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC_US,
            "available_at": _UTC_US,
            "label_end_at": _UTC_US,
            "atr_14": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _write_dataset(storage_root: Path, *, label_kind: str) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(
        _labelled_rows(binary=label_kind == "BINARY"),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )
    dataset_id = "0123456789abcdef" if label_kind == "REGRESSION" else "fedcba9876543210"
    return PredictiveDatasetRepository(storage_root).write(
        PredictiveDatasetEnvelope(
            manifest=PredictiveDatasetManifest(
                schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
                dataset_id=dataset_id,
                study_spec={
                    "study_id": "determinism_fixture",
                    "label": {"kind": label_kind, "horizon": "5m"},
                },
                definition_hash="a" * 64,
                dataset_fingerprint=dataset_id + ("c" * 48),
                source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
                exclusion_counts={
                    "candidate_rows": 40,
                    "labelled_rows": 40,
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


def _spec(family: str, task_type: TaskType) -> EstimatorSpec:
    hyperparameters = {"C": 1.0} if task_type is TaskType.CLASSIFICATION else {"alpha": 1.0}
    return EstimatorSpec(
        family=family,
        hyperparameters=hyperparameters,
        seed=7,
        task_type=task_type,
    )


def _set_nonzero_thread_env(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    for name in _THREAD_POOL_ENV:
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize(
    ("family", "task_type", "label_kind"),
    [
        ("sklearn.ridge", TaskType.REGRESSION, "REGRESSION"),
        ("sklearn.logistic", TaskType.CLASSIFICATION, "BINARY"),
    ],
)
def test_same_spec_and_dataset_fingerprint_yield_identical_predictions_and_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    task_type: TaskType,
    label_kind: str,
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root, label_kind=label_kind)
    dataset = PredictiveDatasetRepository(storage_root).read(dataset_ref)
    spec = _spec(family, task_type)
    _set_nonzero_thread_env(monkeypatch, "8")

    first = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )
    _set_nonzero_thread_env(monkeypatch, "2")
    second = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=False,
            clock=FixedClock(datetime(2024, 7, 2, 12, 0, tzinfo=UTC)),
        )
    )
    analyzed = analyze_predictive_run(
        AnalyzePredictiveRunRequest(
            run_ref=first.run_ref,
            storage_root=storage_root,
            persist=False,
        )
    )

    assert first.envelope.manifest.dataset_fingerprint == dataset.manifest.dataset_fingerprint
    assert second.envelope.manifest.dataset_fingerprint == dataset.manifest.dataset_fingerprint
    assert first.run_id == second.run_id
    assert first.fingerprint == second.fingerprint
    assert analyzed.run_id == first.run_id
    assert_frame_equal(first.envelope.predictions, second.envelope.predictions)
    assert first.envelope.predictions.get_column("y_pred").to_list() == (
        second.envelope.predictions.get_column("y_pred").to_list()
    )
    assert analyzed.report.pooled.keys() == first.metrics.pooled.keys()
