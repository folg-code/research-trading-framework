"""Estimator protocol, spec, and task type for Predictive Research (D-S040-06)."""

from __future__ import annotations

import json
from collections.abc import Mapping
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


class FittedPredictiveEstimator(Protocol):
    """Fitted estimator that can score feature rows."""

    def predict(self, features: np.ndarray) -> np.ndarray: ...

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None: ...

    def describe(self) -> EstimatorDescription: ...


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
