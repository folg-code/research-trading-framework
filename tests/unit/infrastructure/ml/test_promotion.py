"""Promoted-artifact blob read + parameter extraction tests (ADR-0029 §4)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from trading_framework.infrastructure.ml.promotion import (
    PromotedFamilyUnsupportedError,
    PromotionVersionMismatchError,
    extract_promoted_parameters,
)
from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.infrastructure.ml.sklearn.adapter import FittedSklearnEstimator
from trading_framework.research.predictive import (
    EstimatorSpec,
    TaskType,
    default_preprocessing_spec,
)
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_RIDGE_FEATURES = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 1.0], [5.0, 0.0]])
_RIDGE_TARGET = np.array([0.0, 1.5, 2.5, 3.5, 2.0, 1.0])

_LOGISTIC_FEATURES = np.array([[0.0], [1.0], [2.0], [3.0], [10.0], [11.0], [12.0], [13.0]])
_LOGISTIC_TARGET = np.array([0, 0, 0, 0, 1, 1, 1, 1])


@dataclass(frozen=True, slots=True)
class _FakeManifest:
    """Minimal ``PromotedManifestLike`` fixture, per ADR-0029 §9's structural Protocol."""

    model_family: str
    feature_output_refs: tuple[str, ...]
    preprocessing_spec: dict[str, object]
    format_version: str = "v1"
    artifact_fingerprint: str = "test-fingerprint"


def _spec(family: str, task_type: TaskType, **hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family=family, hyperparameters=hyperparameters, seed=7, task_type=task_type
    )


@pytest.mark.parametrize(
    ("family", "task_type", "features", "target", "hyperparameters"),
    (
        ("sklearn.ridge", TaskType.REGRESSION, _RIDGE_FEATURES, _RIDGE_TARGET, {"alpha": 1.0}),
        (
            "sklearn.elastic_net",
            TaskType.REGRESSION,
            _RIDGE_FEATURES,
            _RIDGE_TARGET,
            {"alpha": 0.5, "l1_ratio": 0.5},
        ),
        (
            "sklearn.logistic",
            TaskType.CLASSIFICATION,
            _LOGISTIC_FEATURES,
            _LOGISTIC_TARGET,
            {"C": 1.0},
        ),
    ),
)
def test_round_trip_blob_extract_load_predict(
    family: str,
    task_type: TaskType,
    features: np.ndarray,
    target: np.ndarray,
    hyperparameters: dict[str, object],
) -> None:
    import sklearn

    fitted = resolve_estimator(_spec(family, task_type, **hyperparameters)).fit(
        features, target, None
    )
    assert isinstance(fitted, FittedSklearnEstimator)
    blob = fitted.serialize_artifact()
    preprocessing_spec = default_preprocessing_spec()

    params = extract_promoted_parameters(
        blob,
        model_family=family,
        recorded_library="sklearn",
        recorded_library_version=sklearn.__version__,
        preprocessing_spec=preprocessing_spec,
    )

    # Extracted statistics equal FittedSklearnPreprocessor.statistics() exactly.
    expected_statistics = fitted.preprocessing_statistics()
    if "impute_median" in expected_statistics:
        assert params.impute_median == tuple(expected_statistics["impute_median"])
    if "standardize_mean" in expected_statistics:
        assert params.standardize_mean == tuple(expected_statistics["standardize_mean"])
    if "standardize_scale" in expected_statistics:
        assert params.standardize_scale == tuple(expected_statistics["standardize_scale"])

    manifest = _FakeManifest(
        model_family=family,
        feature_output_refs=tuple(f"feature_{i}" for i in range(features.shape[1])),
        preprocessing_spec=preprocessing_spec.to_dict(),
    )
    predictor = load_promoted_artifact(manifest, params)
    predicted = predictor.predict(features)

    np.testing.assert_array_equal(predicted, fitted.predict(features))


def test_tree_family_raises_promoted_family_unsupported_error_naming_family_and_deferral() -> None:
    with pytest.raises(PromotedFamilyUnsupportedError) as caught:
        extract_promoted_parameters(
            b"irrelevant, refused before any blob read",
            model_family="xgboost.regressor",
            recorded_library="sklearn",
            recorded_library_version="0.0.0",
            preprocessing_spec=default_preprocessing_spec(),
        )
    message = str(caught.value)
    assert "xgboost.regressor" in message
    assert "deferred" in message


def test_neural_family_raises_promoted_family_unsupported_error_naming_deferral() -> None:
    with pytest.raises(PromotedFamilyUnsupportedError) as caught:
        extract_promoted_parameters(
            b"irrelevant, refused before any blob read",
            model_family="torch.feedforward.classifier",
            recorded_library="torch",
            recorded_library_version="0.0.0",
            preprocessing_spec=default_preprocessing_spec(),
        )
    message = str(caught.value)
    assert "torch.feedforward.classifier" in message
    assert "deferred" in message


def test_library_version_mismatch_raises_before_unpickling_and_names_remedy() -> None:
    garbage_blob = b"not a valid joblib payload; unpickling this must never be attempted"
    with pytest.raises(PromotionVersionMismatchError) as caught:
        extract_promoted_parameters(
            garbage_blob,
            model_family="sklearn.ridge",
            recorded_library="sklearn",
            recorded_library_version="0.0.0-does-not-exist",
            preprocessing_spec=default_preprocessing_spec(),
        )
    message = str(caught.value)
    assert "0.0.0-does-not-exist" in message
    assert "re-run" in message.lower()


def test_non_sklearn_training_library_raises_version_mismatch_before_unpickling() -> None:
    garbage_blob = b"not a valid joblib payload; unpickling this must never be attempted"
    with pytest.raises(PromotionVersionMismatchError) as caught:
        extract_promoted_parameters(
            garbage_blob,
            model_family="sklearn.ridge",
            recorded_library="torch",
            recorded_library_version="2.0.0",
            preprocessing_spec=default_preprocessing_spec(),
        )
    assert "torch" in str(caught.value)


def test_blob_family_mismatch_with_declared_family_is_refused() -> None:
    fitted = resolve_estimator(_spec("sklearn.ridge", TaskType.REGRESSION, alpha=1.0)).fit(
        _RIDGE_FEATURES, _RIDGE_TARGET, None
    )
    assert isinstance(fitted, FittedSklearnEstimator)
    blob = fitted.serialize_artifact()
    import sklearn

    from trading_framework.research.predictive.errors import PredictiveSpecError

    with pytest.raises(PredictiveSpecError):
        extract_promoted_parameters(
            blob,
            model_family="sklearn.elastic_net",
            recorded_library="sklearn",
            recorded_library_version=sklearn.__version__,
            preprocessing_spec=default_preprocessing_spec(),
        )
