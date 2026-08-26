"""Out-of-sample permutation importance for Predictive Research (D-S042-12).

Numpy only. Scores ``predict()`` output with the same primary metrics used
for bounded selection. Application supplies TEST rows; this module does not
import adapters.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import NativeFeatureImportance
from trading_framework.research.predictive.metrics import selection_metric_value

DEFAULT_PERMUTATION_REPEATS = 5


@dataclass(frozen=True, slots=True)
class PermutationImportance:
    """Mean drop in the primary metric when each TEST column is shuffled."""

    feature_names: tuple[str, ...]
    importances_mean: tuple[float, ...]
    importances_std: tuple[float, ...]
    n_repeats: int
    seed: int
    metric: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_names": list(self.feature_names),
            "importances_mean": list(self.importances_mean),
            "importances_std": list(self.importances_std),
            "n_repeats": self.n_repeats,
            "seed": self.seed,
            "metric": self.metric,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PermutationImportance:
        return cls(
            feature_names=_string_tuple(payload.get("feature_names"), "feature_names"),
            importances_mean=_float_tuple(payload.get("importances_mean"), "importances_mean"),
            importances_std=_float_tuple(payload.get("importances_std"), "importances_std"),
            n_repeats=_require_int(payload.get("n_repeats"), "n_repeats"),
            seed=_require_int(payload.get("seed"), "seed"),
            metric=str(payload.get("metric", "")),
        )


@dataclass(frozen=True, slots=True)
class FoldPrimaryGap:
    """Primary metric on outer TRAIN vs outer TEST for one fold."""

    train_primary: float | None
    test_primary: float | None
    primary_gap: float | None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "train_primary": self.train_primary,
            "test_primary": self.test_primary,
            "primary_gap": self.primary_gap,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FoldPrimaryGap:
        return cls(
            train_primary=_optional_float(payload.get("train_primary")),
            test_primary=_optional_float(payload.get("test_primary")),
            primary_gap=_optional_float(payload.get("primary_gap")),
        )


@dataclass(frozen=True, slots=True)
class FoldImportanceRecord:
    """Native + permutation importance and the train/test gap for one fold."""

    fold_id: int
    native: NativeFeatureImportance | None
    permutation: PermutationImportance
    primary_gap: FoldPrimaryGap

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "native": None if self.native is None else self.native.to_dict(),
            "permutation": self.permutation.to_dict(),
            "train_primary": self.primary_gap.train_primary,
            "test_primary": self.primary_gap.test_primary,
            "primary_gap": self.primary_gap.primary_gap,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FoldImportanceRecord:
        native_raw = payload.get("native")
        permutation_raw = payload.get("permutation")
        if not isinstance(permutation_raw, Mapping):
            msg = "permutation importance must be a mapping"
            raise PredictiveSpecError(msg)
        native = None
        if native_raw is not None:
            if not isinstance(native_raw, Mapping):
                msg = "native importance must be a mapping or null"
                raise PredictiveSpecError(msg)
            native = NativeFeatureImportance.from_dict(native_raw)
        return cls(
            fold_id=_require_int(payload.get("fold_id"), "fold_id"),
            native=native,
            permutation=PermutationImportance.from_dict(permutation_raw),
            primary_gap=FoldPrimaryGap.from_dict(payload),
        )


@dataclass(frozen=True, slots=True)
class ImportanceTrace:
    """Persisted importance sidecar next to a predictive run."""

    metric: str
    n_repeats: int
    folds: tuple[FoldImportanceRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "n_repeats": self.n_repeats,
            "folds": [fold.to_dict() for fold in self.folds],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImportanceTrace:
        folds_raw = payload.get("folds")
        if not isinstance(folds_raw, Sequence) or isinstance(folds_raw, (str, bytes)):
            msg = "importance folds must be a sequence"
            raise PredictiveSpecError(msg)
        folds = tuple(
            FoldImportanceRecord.from_dict(_require_mapping(item, "fold")) for item in folds_raw
        )
        return cls(
            metric=str(payload.get("metric", "")),
            n_repeats=_require_int(payload.get("n_repeats"), "n_repeats"),
            folds=folds,
        )


def permutation_feature_importance(
    features: np.ndarray,
    y_true: np.ndarray,
    *,
    predict: Callable[[np.ndarray], np.ndarray],
    metric: str,
    seed: int,
    n_repeats: int = DEFAULT_PERMUTATION_REPEATS,
    feature_names: Sequence[str] | None = None,
    predict_score: Callable[[np.ndarray], np.ndarray] | None = None,
) -> PermutationImportance:
    """Shuffle each TEST column independently; importance is baseline minus shuffled."""
    matrix = np.asarray(features, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        msg = "permutation importance requires a non-empty 2-d feature matrix"
        raise PredictiveSpecError(msg)
    if n_repeats < 1:
        msg = "n_repeats must be at least 1"
        raise PredictiveSpecError(msg)
    n_features = int(matrix.shape[1])
    names = _feature_names(feature_names, n_features)
    baseline = _score_matrix(
        matrix,
        y_true,
        predict=predict,
        metric=metric,
        predict_score=predict_score,
    )
    rng = np.random.default_rng(int(seed))
    means: list[float] = []
    stds: list[float] = []
    for column in range(n_features):
        drops: list[float] = []
        for _repeat in range(n_repeats):
            shuffled = matrix.copy()
            shuffled[:, column] = rng.permutation(shuffled[:, column])
            shuffled_score = _score_matrix(
                shuffled,
                y_true,
                predict=predict,
                metric=metric,
                predict_score=predict_score,
            )
            if baseline is None or shuffled_score is None:
                continue
            drops.append(baseline - shuffled_score)
        if not drops:
            means.append(0.0)
            stds.append(0.0)
            continue
        values = np.asarray(drops, dtype=np.float64)
        means.append(float(values.mean()))
        stds.append(float(values.std(ddof=0)))
    return PermutationImportance(
        feature_names=names,
        importances_mean=tuple(means),
        importances_std=tuple(stds),
        n_repeats=n_repeats,
        seed=int(seed),
        metric=metric,
    )


def primary_gap(
    *,
    train_score: float | None,
    test_score: float | None,
) -> FoldPrimaryGap:
    """Absolute train-minus-test gap on the primary metric."""
    gap = None if train_score is None or test_score is None else abs(train_score - test_score)
    return FoldPrimaryGap(train_primary=train_score, test_primary=test_score, primary_gap=gap)


def _score_matrix(
    features: np.ndarray,
    y_true: np.ndarray,
    *,
    predict: Callable[[np.ndarray], np.ndarray],
    metric: str,
    predict_score: Callable[[np.ndarray], np.ndarray] | None,
) -> float | None:
    predicted = np.asarray(predict(features), dtype=np.float64).reshape(-1)
    scores = None
    if predict_score is not None:
        scores = np.asarray(predict_score(features), dtype=np.float64)
    return selection_metric_value(metric, y_true=y_true, y_pred=predicted, y_score=scores)


def _feature_names(names: Sequence[str] | None, n_features: int) -> tuple[str, ...]:
    if names is None:
        return tuple(f"f{index}" for index in range(n_features))
    if len(names) != n_features:
        msg = f"feature_names length {len(names)} does not match columns {n_features}"
        raise PredictiveSpecError(msg)
    return tuple(str(name) for name in names)


def _require_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        msg = f"{field_name} must be a mapping"
        raise PredictiveSpecError(msg)
    return value


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "expected a finite number or null"
        raise PredictiveSpecError(msg)
    return float(value)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        msg = f"{field_name} must be a sequence of strings"
        raise PredictiveSpecError(msg)
    return tuple(str(item) for item in value)


def _float_tuple(value: object, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        msg = f"{field_name} must be a sequence of numbers"
        raise PredictiveSpecError(msg)
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            msg = f"{field_name} must be a sequence of numbers"
            raise PredictiveSpecError(msg)
        numbers.append(float(item))
    return tuple(numbers)
