"""Tests for Predictive Research run identity fingerprinting (D-S040-18)."""

from __future__ import annotations

import hashlib
import json

from trading_framework import __version__ as framework_version
from trading_framework.research.datasets.predictive_run import (
    RUN_ID_HEX_LENGTH,
    compute_run_fingerprint,
    derive_predictive_run_id,
)
from trading_framework.research.predictive import (
    EstimatorSpec,
    PreprocessingSpec,
    PreprocessingStep,
    TaskType,
    default_preprocessing_spec,
)


def _ridge_spec(*, seed: int = 7, alpha: float = 1.0) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": alpha},
        seed=seed,
        task_type=TaskType.REGRESSION,
    )


def test_run_fingerprint_is_stable_and_ignores_prediction_bytes() -> None:
    first = compute_run_fingerprint(
        dataset_fingerprint="a" * 64,
        estimator_spec=_ridge_spec(),
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    second = compute_run_fingerprint(
        dataset_fingerprint="a" * 64,
        estimator_spec=_ridge_spec(),
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    assert first == second
    assert len(first) == 64
    assert derive_predictive_run_id(first) == first[:RUN_ID_HEX_LENGTH]


def test_run_fingerprint_matches_canonical_payload_hash() -> None:
    spec = _ridge_spec()
    preprocessing = default_preprocessing_spec()
    payload = {
        "dataset_fingerprint": "b" * 64,
        "estimator_spec": spec.to_dict(),
        "preprocessing_spec": preprocessing.identity_payload(),
        "library": "sklearn",
        "library_version": "1.6.1",
        "framework_version": "0.1.0",
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert (
        compute_run_fingerprint(
            dataset_fingerprint="b" * 64,
            estimator_spec=spec,
            preprocessing_spec=preprocessing,
            library="sklearn",
            library_version="1.6.1",
            framework_version="0.1.0",
        )
        == expected
    )


def test_run_fingerprint_changes_with_seed_library_and_preprocessing() -> None:
    baseline = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=_ridge_spec(seed=1),
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    seed_changed = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=_ridge_spec(seed=2),
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    library_changed = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=_ridge_spec(seed=1),
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.7.0",
        framework_version=framework_version,
    )
    preprocessing_changed = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=_ridge_spec(seed=1),
        preprocessing_spec=PreprocessingSpec(steps=(PreprocessingStep.IMPUTE_MEDIAN,)),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    assert seed_changed != baseline
    assert library_changed != baseline
    assert preprocessing_changed != baseline
    assert derive_predictive_run_id(seed_changed) != derive_predictive_run_id(baseline)


def test_run_fingerprint_includes_candidate_set() -> None:
    from trading_framework.research.predictive import CandidateSetSpec, SelectionMetric

    spec = _ridge_spec()
    candidate_set = CandidateSetSpec(
        candidates=(spec, _ridge_spec(alpha=2.0)),
        selection_metric=SelectionMetric.SPEARMAN_IC,
    ).to_dict()
    without_set = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=spec,
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
    )
    with_set = compute_run_fingerprint(
        dataset_fingerprint="c" * 64,
        estimator_spec=spec,
        preprocessing_spec=default_preprocessing_spec(),
        library="sklearn",
        library_version="1.6.0",
        framework_version=framework_version,
        candidate_set=candidate_set,
    )
    assert with_set != without_set


def test_run_fingerprint_includes_sequence_window_spec() -> None:
    spec = _ridge_spec()
    preprocessing = default_preprocessing_spec()
    window_payload = {"lookback_bars": 4, "stride": 1, "padding_policy": "DROP"}
    without_windows = compute_run_fingerprint(
        dataset_fingerprint="d" * 64,
        estimator_spec=spec,
        preprocessing_spec=preprocessing,
        library="torch",
        library_version="2.6.0",
        framework_version=framework_version,
    )
    with_windows = compute_run_fingerprint(
        dataset_fingerprint="d" * 64,
        estimator_spec=spec,
        preprocessing_spec=preprocessing,
        library="torch",
        library_version="2.6.0",
        framework_version=framework_version,
        sequence_window_spec=window_payload,
    )
    payload = {
        "dataset_fingerprint": "d" * 64,
        "estimator_spec": spec.to_dict(),
        "preprocessing_spec": preprocessing.identity_payload(),
        "library": "torch",
        "library_version": "2.6.0",
        "framework_version": framework_version,
        "sequence_window_spec": window_payload,
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert with_windows != without_windows
    assert with_windows == expected
