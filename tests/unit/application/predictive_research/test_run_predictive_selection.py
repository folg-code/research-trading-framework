"""Bounded candidate selection inside Predictive Research runs (D-S042-11)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    RunPredictiveResearchRequest,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_selection_path
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
    CandidateSetSpec,
    EstimatorDescription,
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    SelectionMetric,
    TaskType,
    require_early_stopping_eval_roles,
)
from trading_framework.time.clocks.fixed import FixedClock

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")

_RUN_IMPL = __import__(
    "trading_framework.application.predictive_research.run_predictive_research",
    fromlist=["run_predictive_research"],
)


class _SignedFitted:
    def __init__(self, sign: float) -> None:
        self._sign = sign

    def predict(self, features: np.ndarray) -> np.ndarray:
        return self._sign * np.asarray(features[:, 0], dtype=np.float64)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        return None

    def describe(self) -> EstimatorDescription:
        return EstimatorDescription(
            library="testlib",
            version="0.0",
            resolved_params={"sign": self._sign},
        )

    def native_feature_importance(self) -> object | None:
        return None


class _SignedEstimator:
    def __init__(self, sign: float) -> None:
        self._sign = sign
        self.fit_row_counts: list[int] = []
        self.fit_roles: list[tuple[str, ...]] = []

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> _SignedFitted:
        assert isinstance(sample_metadata, tuple)
        self.fit_row_counts.append(int(features.shape[0]))
        self.fit_roles.append(
            tuple(
                role.value if isinstance(role, FoldRole) else str(role) for role in sample_metadata
            )
        )
        return _SignedFitted(self._sign)


def _rows(*, n_train: int = 50, n_test: int = 12) -> pl.DataFrame:
    count = n_train + n_test
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    feature = [float(index) for index in range(count)]
    labels = [0.01 * index for index in range(count)]
    roles = [FoldRole.TRAIN.value] * n_train + [FoldRole.TEST.value] * n_test
    return pl.DataFrame(
        {
            "entity_id": [stamp.isoformat() for stamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [stamp + timedelta(minutes=5) for stamp in timestamps],
            "atr_14": feature,
            "label": labels,
            "forward_return": labels,
            "outcome_status": ["COMPLETE"] * count,
            "fold_id": [1] * count,
            "fold_role": roles,
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
            "fold_id": pl.Int64(),
            "fold_role": pl.String(),
        },
    )


def _write_dataset(storage_root: Path) -> PredictiveDatasetRef:
    features = _rows()
    envelope = PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id="0123456789abcdef",
            study_spec={
                "study_id": "selection_fixture",
                "label": {"kind": "REGRESSION", "horizon": "5m"},
            },
            definition_hash="a" * 64,
            dataset_fingerprint="c" * 64,
            source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
            exclusion_counts={
                "candidate_rows": 62,
                "labelled_rows": 62,
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
    return PredictiveDatasetRepository(storage_root).write(envelope)


def _ridge(*, alpha: float) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": alpha},
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def test_candidate_selection_refits_winner_and_predicts_test_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    estimators: dict[float, _SignedEstimator] = {}

    def fake_resolve(spec: EstimatorSpec, *, preprocessing: object = None) -> _SignedEstimator:
        assert preprocessing is not None
        alpha = float(spec.hyperparameters["alpha"])
        sign = 1.0 if alpha >= 1.0 else -1.0
        estimator = _SignedEstimator(sign)
        estimators.setdefault(alpha, estimator)
        # Each resolve gets a fresh recorder so inner vs refit counts stay local;
        # keep the last instance per alpha for assertions.
        estimators[alpha] = estimator
        return estimator

    monkeypatch.setattr(_RUN_IMPL, "resolve_estimator", fake_resolve)
    monkeypatch.setattr(_RUN_IMPL, "dump_fitted_estimator", lambda _fitted: b"opaque-artifact")

    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root)
    candidate_set = CandidateSetSpec(
        candidates=(_ridge(alpha=0.5), _ridge(alpha=1.5)),
        selection_metric=SelectionMetric.SPEARMAN_IC,
        early_stopping_rounds=5,
    )
    result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=_ridge(alpha=0.5),
            storage_root=storage_root,
            candidate_set=candidate_set,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )
    assert result.selection_trace is not None
    fold_trace = result.selection_trace.folds[0]
    assert fold_trace.winner.hyperparameters["alpha"] == 1.5
    assert fold_trace.candidates[1].selected is True
    assert fold_trace.candidates[0].selected is False
    assert result.envelope.predictions.get_column("fold_id").n_unique() == 1
    assert result.envelope.manifest.estimator_spec["hyperparameters"]["alpha"] == 1.5
    assert result.envelope.manifest.candidate_set is not None
    selection_path = predictive_research_run_selection_path(storage_root, result.run_id)
    payload = json.loads(selection_path.read_text(encoding="utf-8"))
    assert payload["folds"][0]["winner"]["hyperparameters"]["alpha"] == 1.5
    for estimator in estimators.values():
        assert all(role == FoldRole.TRAIN.value for roles in estimator.fit_roles for role in roles)
        assert FoldRole.TEST.value not in {role for roles in estimator.fit_roles for role in roles}


def test_selection_rejects_outer_test_early_stopping() -> None:
    with pytest.raises(PredictiveSpecError, match="cannot reference outer TEST"):
        require_early_stopping_eval_roles((FoldRole.TEST,))


def test_inner_split_too_small_is_spec_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        _RUN_IMPL,
        "resolve_estimator",
        lambda spec, *, preprocessing=None: _SignedEstimator(1.0),
    )
    monkeypatch.setattr(_RUN_IMPL, "dump_fitted_estimator", lambda _fitted: b"blob")
    storage_root = tmp_path / "workspace"
    # Reuse the helper but the default fixture has 50 TRAIN rows. Build a tiny one.
    features = _rows(n_train=12, n_test=8)
    envelope = PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id="fedcba9876543210",
            study_spec={"study_id": "tiny", "label": {"kind": "REGRESSION", "horizon": "5m"}},
            definition_hash="a" * 64,
            dataset_fingerprint="d" * 64,
            source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
            exclusion_counts={
                "candidate_rows": 20,
                "labelled_rows": 20,
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
    dataset_ref = PredictiveDatasetRepository(storage_root).write(envelope)
    with pytest.raises(PredictiveSpecError, match="inner split"):
        run_predictive_research(
            RunPredictiveResearchRequest(
                dataset_ref=dataset_ref,
                estimator=_ridge(alpha=1.0),
                storage_root=storage_root,
                candidate_set=CandidateSetSpec(candidates=(_ridge(alpha=1.0), _ridge(alpha=2.0))),
                persist=False,
            )
        )
