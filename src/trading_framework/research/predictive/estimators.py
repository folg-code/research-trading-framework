"""Estimator protocol, spec, and task type for Predictive Research (D-S040-06)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

import numpy as np

from trading_framework.research.predictive.errors import PredictiveSpecError


class TaskType(StrEnum):
    """Learning task declared on an estimator spec."""

    REGRESSION = "REGRESSION"
    CLASSIFICATION = "CLASSIFICATION"


@dataclass(frozen=True, slots=True)
class EstimatorDescription:
    """Persisted identity of a fitted estimator.

    ``describe()`` output is stored with the run. An unrecorded hyperparameter
    breaks reproducibility.
    """

    library: str
    version: str
    resolved_params: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolved_params", _freeze_mapping(self.resolved_params))


@dataclass(frozen=True, slots=True)
class EstimatorSpec:
    """Frozen estimator identity hashed into a future predictive run.

    ``family`` is a registry identifier (for example ``sklearn.ridge``).
    ``hyperparameters`` are canonical JSON-stable values. ``seed`` is required;
    unseeded specs are invalid.
    """

    family: str
    hyperparameters: Mapping[str, Any]
    seed: int
    task_type: TaskType

    def __post_init__(self) -> None:
        family = self.family.strip()
        if not family:
            msg = "estimator family must be non-empty"
            raise PredictiveSpecError(msg)
        if family != self.family:
            object.__setattr__(self, "family", family)
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            msg = "estimator seed must be an integer"
            raise PredictiveSpecError(msg)
        object.__setattr__(
            self,
            "hyperparameters",
            _canonicalize_hyperparameters(self.hyperparameters),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "hyperparameters": dict(self.hyperparameters),
            "seed": self.seed,
            "task_type": self.task_type.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EstimatorSpec:
        try:
            family = str(payload["family"])
            hyperparameters = payload["hyperparameters"]
            seed = payload["seed"]
            task_type_raw = payload["task_type"]
        except KeyError as exc:
            msg = f"estimator spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        if not isinstance(hyperparameters, Mapping):
            msg = "estimator hyperparameters must be a mapping"
            raise PredictiveSpecError(msg)
        try:
            task_type = TaskType(str(task_type_raw))
        except ValueError as exc:
            msg = f"invalid estimator task_type: {task_type_raw!r}"
            raise PredictiveSpecError(msg) from exc
        return cls(
            family=family,
            hyperparameters=hyperparameters,
            seed=_require_int(seed, field_name="seed"),
            task_type=task_type,
        )


@dataclass(frozen=True, slots=True)
class NativeFeatureImportance:
    """Library-native gain / split scores, aligned to feature columns (D-S042-12).

    Training-fold statistics. Displayed beside permutation importance; not the
    conclusion on their own.
    """

    feature_names: tuple[str, ...]
    gain: tuple[float, ...]
    split: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if len(self.feature_names) != len(self.gain):
            msg = "native importance feature_names and gain must be the same length"
            raise PredictiveSpecError(msg)
        if self.split is not None and len(self.split) != len(self.gain):
            msg = "native importance split scores must match gain length"
            raise PredictiveSpecError(msg)

    def relabel(self, feature_names: tuple[str, ...]) -> NativeFeatureImportance:
        if len(feature_names) != len(self.gain):
            msg = (
                f"cannot relabel native importance: got {len(feature_names)} names "
                f"for {len(self.gain)} scores"
            )
            raise PredictiveSpecError(msg)
        return NativeFeatureImportance(
            feature_names=feature_names,
            gain=self.gain,
            split=self.split,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "feature_names": list(self.feature_names),
            "gain": list(self.gain),
        }
        if self.split is not None:
            payload["split"] = list(self.split)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NativeFeatureImportance:
        split_raw = payload.get("split")
        split = None if split_raw is None else _float_tuple(split_raw, "split")
        return cls(
            feature_names=_string_tuple(payload.get("feature_names"), "feature_names"),
            gain=_float_tuple(payload.get("gain"), "gain"),
            split=split,
        )


class FittedPredictiveEstimator(Protocol):
    """Fitted estimator that can score feature rows.

    ``native_feature_importance()`` is optional at the value level: sklearn
    adapters return ``None``. Tree adapters return scores after ``fit()``.
    """

    def predict(self, features: np.ndarray) -> np.ndarray: ...

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None: ...

    def describe(self) -> EstimatorDescription: ...

    def native_feature_importance(self) -> NativeFeatureImportance | None: ...


class PredictiveEstimator(Protocol):
    """Unfitted estimator selected by family identifier.

    Structural protocol — implementations do not subclass sklearn types.
    """

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> FittedPredictiveEstimator: ...


def _canonicalize_hyperparameters(values: object) -> Mapping[str, Any]:
    if not isinstance(values, Mapping):
        msg = "estimator hyperparameters must be a mapping"
        raise PredictiveSpecError(msg)
    try:
        canonical = json.dumps(dict(values), sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        msg = "estimator hyperparameters must be JSON-serializable"
        raise PredictiveSpecError(msg) from exc
    loaded = json.loads(canonical)
    if not isinstance(loaded, dict):
        msg = "estimator hyperparameters must be a mapping"
        raise PredictiveSpecError(msg)
    return MappingProxyType(loaded)


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value


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
