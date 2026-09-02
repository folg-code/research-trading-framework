"""Evaluator exactness suite (Sprint 049 T010a, default CI, no ML extra).

De-risks the maintainer's named riskiest assumption without needing sklearn
to agree: every assertion here is bitwise (``==`` on float64), never
``pytest.approx``, and every expected value is computed independently of the
evaluator's own code, directly inside the test.
"""

from __future__ import annotations

import math

import numpy as np

from tests.unit.research.predictive._promoted_artifact_fixtures import _manifest
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact
from trading_framework.research.predictive.promotion.parameters import (
    PromotedArtifactParameters,
)


def test_linear_path_evaluates_to_independently_computed_values() -> None:
    """impute median -> standardize -> ``X @ coef + intercept``, no sigmoid."""
    manifest = _manifest(model_family="sklearn.ridge", n_features=2)
    payload = PromotedArtifactParameters(
        coefficients=(3.0, -1.0),
        intercept=0.5,
        impute_median=(1.0, 2.0),
        standardize_mean=(1.0, 2.0),
        standardize_scale=(2.0, 4.0),
    )
    predictor = load_promoted_artifact(manifest, payload)

    features = np.array([[1.0, np.nan], [5.0, 10.0]], dtype=np.float64)
    predicted = predictor.predict(features)

    # Row 1: impute col1 -> 2.0 (the fixture's median). z = ((1-1)/2, (2-2)/4) = (0, 0).
    #   y = 0*3 + 0*-1 + 0.5 = 0.5
    # Row 2: no imputation needed. z = ((5-1)/2, (10-2)/4) = (2, 2).
    #   y = 2*3 + 2*-1 + 0.5 = 6 - 2 + 0.5 = 4.5
    expected = np.array([0.5, 4.5], dtype=np.float64)
    np.testing.assert_array_equal(predicted, expected)


def test_logistic_path_decision_function_and_probability_are_exact() -> None:
    """The sigmoid is applied only for sklearn.logistic, on top of the same y."""
    manifest = _manifest(model_family="sklearn.logistic", n_features=1)
    payload = PromotedArtifactParameters(
        coefficients=(2.0,),
        intercept=0.0,
        standardize_mean=(0.0,),
        standardize_scale=(1.0,),
    )
    predictor = load_promoted_artifact(manifest, payload)

    features = np.array([[1.0], [-1.0], [0.0]], dtype=np.float64)
    z = predictor.decision_function(features)  # type: ignore[attr-defined]
    proba = predictor.predict_proba(features)  # type: ignore[attr-defined]
    label = predictor.predict(features)

    expected_z = np.array([2.0, -2.0, 0.0], dtype=np.float64)
    np.testing.assert_array_equal(z, expected_z)

    # Computed independently with math.exp, never by re-calling the evaluator.
    expected_proba = np.array(
        [1.0 / (1.0 + math.exp(-2.0)), 1.0 / (1.0 + math.exp(2.0)), 0.5],
        dtype=np.float64,
    )
    np.testing.assert_array_equal(proba, expected_proba)

    # z == 0 must resolve to the positive class (>=0), never a coin flip.
    expected_label = np.array([1.0, 0.0, 1.0], dtype=np.float64)
    np.testing.assert_array_equal(label, expected_label)


def test_all_nan_column_is_fully_imputed() -> None:
    """A column that is entirely NaN at predict time is still substituted."""
    manifest = _manifest(model_family="sklearn.ridge", n_features=2)
    payload = PromotedArtifactParameters(
        coefficients=(1.0, 1.0),
        intercept=0.0,
        impute_median=(5.0, -3.0),
        standardize_mean=(0.0, 0.0),
        standardize_scale=(1.0, 1.0),
    )
    predictor = load_promoted_artifact(manifest, payload)

    features = np.array([[1.0, np.nan], [2.0, np.nan]], dtype=np.float64)
    predicted = predictor.predict(features)

    # col1 is entirely substituted with -3.0. y = x0*1 + (-3.0)*1 + 0
    expected = np.array([1.0 - 3.0, 2.0 - 3.0], dtype=np.float64)
    np.testing.assert_array_equal(predicted, expected)


def test_zero_variance_column_uses_scale_one_substitution() -> None:
    """A fitted ``standardize_scale`` of 1.0 (the zero-variance substitution) is
    applied as a plain identity division, never a divide-by-zero."""
    manifest = _manifest(model_family="sklearn.ridge", n_features=1)
    payload = PromotedArtifactParameters(
        coefficients=(4.0,),
        intercept=1.0,
        standardize_mean=(2.0,),
        standardize_scale=(1.0,),
    )
    predictor = load_promoted_artifact(manifest, payload)

    features = np.array([[2.0], [7.0]], dtype=np.float64)
    predicted = predictor.predict(features)

    # z = (x - 2.0) / 1.0 = x - 2.0. y = z*4 + 1
    expected = np.array([(2.0 - 2.0) * 4.0 + 1.0, (7.0 - 2.0) * 4.0 + 1.0], dtype=np.float64)
    np.testing.assert_array_equal(predicted, expected)


def test_single_row_matrix_evaluates_exactly() -> None:
    manifest = _manifest(model_family="sklearn.elastic_net", n_features=3)
    payload = PromotedArtifactParameters(
        coefficients=(1.0, 2.0, 3.0),
        intercept=-6.0,
        standardize_mean=(0.0, 0.0, 0.0),
        standardize_scale=(1.0, 1.0, 1.0),
    )
    predictor = load_promoted_artifact(manifest, payload)

    features = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
    predicted = predictor.predict(features)

    # y = 1*1 + 1*2 + 1*3 - 6 = 0.0
    np.testing.assert_array_equal(predicted, np.array([0.0], dtype=np.float64))


def test_repeated_evaluation_is_deterministic() -> None:
    manifest = _manifest(model_family="sklearn.ridge", n_features=2)
    payload = PromotedArtifactParameters(
        coefficients=(1.5, -2.5),
        intercept=0.25,
        standardize_mean=(0.0, 0.0),
        standardize_scale=(1.0, 1.0),
    )
    predictor = load_promoted_artifact(manifest, payload)
    features = np.array([[3.0, 1.0], [-1.0, 4.0]], dtype=np.float64)

    first = predictor.predict(features)
    second = predictor.predict(features)
    third = predictor.predict(features)

    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(second, third)
