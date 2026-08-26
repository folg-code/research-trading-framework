"""Permutation importance and train/test primary-metric gap (D-S042-12)."""

from __future__ import annotations

import numpy as np
import pytest

from trading_framework.research.predictive import (
    NativeFeatureImportance,
    PredictiveSpecError,
    permutation_feature_importance,
    primary_gap,
)


def test_permutation_importance_flags_the_informative_column() -> None:
    features = np.column_stack(
        [
            np.linspace(0.0, 1.0, 40),
            np.zeros(40),
        ]
    )
    target = features[:, 0].copy()

    def predict(matrix: np.ndarray) -> np.ndarray:
        return np.asarray(matrix[:, 0], dtype=np.float64)

    result = permutation_feature_importance(
        features,
        target,
        predict=predict,
        metric="spearman_ic",
        seed=7,
        n_repeats=5,
        feature_names=("signal", "noise"),
    )
    assert result.feature_names == ("signal", "noise")
    assert result.importances_mean[0] > result.importances_mean[1]


def test_permutation_importance_does_not_mutate_features() -> None:
    features = np.arange(20, dtype=np.float64).reshape(10, 2)
    original = features.copy()
    target = features[:, 0].copy()

    def predict(matrix: np.ndarray) -> np.ndarray:
        return np.asarray(matrix[:, 0], dtype=np.float64)

    permutation_feature_importance(
        features, target, predict=predict, metric="spearman_ic", seed=3, n_repeats=2
    )
    np.testing.assert_array_equal(features, original)


def test_permutation_importance_rejects_empty_matrix() -> None:
    with pytest.raises(PredictiveSpecError, match="non-empty 2-d"):
        permutation_feature_importance(
            np.zeros((0, 2)),
            np.zeros(0),
            predict=lambda matrix: matrix[:, 0],
            metric="spearman_ic",
            seed=1,
        )


def test_native_importance_relabel_rewrites_names() -> None:
    native = NativeFeatureImportance(feature_names=("f0", "f1"), gain=(1.0, 0.0), split=(3.0, 1.0))
    relabelled = native.relabel(("signal", "noise"))
    assert relabelled.feature_names == ("signal", "noise")
    assert relabelled.gain == native.gain
    assert relabelled.split == native.split


def test_native_importance_to_dict_omits_missing_split() -> None:
    payload = NativeFeatureImportance(feature_names=("a",), gain=(1.0,)).to_dict()
    assert payload == {"feature_names": ["a"], "gain": [1.0]}
    restored = NativeFeatureImportance.from_dict(payload)
    assert restored.feature_names == ("a",)
    assert restored.gain == (1.0,)
    assert restored.split is None


def test_primary_gap_is_none_when_a_score_is_missing() -> None:
    gap = primary_gap(train_score=0.8, test_score=None)
    assert gap.primary_gap is None


def test_permutation_importance_is_seed_stable() -> None:
    features = np.arange(30, dtype=np.float64).reshape(10, 3)
    target = features[:, 0] - features[:, 1]

    def predict(matrix: np.ndarray) -> np.ndarray:
        return np.asarray(matrix[:, 0] - matrix[:, 1], dtype=np.float64)

    first = permutation_feature_importance(
        features, target, predict=predict, metric="spearman_ic", seed=13, n_repeats=3
    )
    second = permutation_feature_importance(
        features, target, predict=predict, metric="spearman_ic", seed=13, n_repeats=3
    )
    assert first.importances_mean == second.importances_mean


def test_primary_gap_is_absolute() -> None:
    gap = primary_gap(train_score=0.9, test_score=0.4)
    assert gap.train_primary == 0.9
    assert gap.test_primary == 0.4
    assert gap.primary_gap == pytest.approx(0.5)


def test_native_importance_rejects_length_mismatch() -> None:
    with pytest.raises(PredictiveSpecError, match="same length"):
        NativeFeatureImportance(feature_names=("a",), gain=(1.0, 2.0))
