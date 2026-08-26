"""Bounded candidate selection for Predictive Research (D-S042-11).

Library-free: numpy and framework contracts only. Application fits and scores
candidates; this module validates the declared set, splits inner train /
validation indices, ranks scores, and rejects outer-TEST early stopping.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec, TaskType
from trading_framework.research.predictive.splitting import FoldRole

DEFAULT_MAX_CANDIDATES = 8
MAX_CANDIDATES_CAP = 16
DEFAULT_INNER_VALIDATION_FRACTION = 0.20
MIN_INNER_SPLIT_ROWS = 10


class SelectionMetric(StrEnum):
    """Primary metric used to pick a candidate inside an outer TRAIN fold."""

    SPEARMAN_IC = "spearman_ic"
    ROC_AUC = "roc_auc"


_METRIC_BY_TASK: Mapping[TaskType, SelectionMetric] = {
    TaskType.REGRESSION: SelectionMetric.SPEARMAN_IC,
    TaskType.CLASSIFICATION: SelectionMetric.ROC_AUC,
}


@dataclass(frozen=True, slots=True)
class CandidateSetSpec:
    """Declared, capped hyperparameter candidates (D-S042-11).

    Exceeding ``max_candidates`` is ``PredictiveSpecError``, not silent
    truncation. A run without this spec keeps the S040 single-estimator path.
    """

    candidates: tuple[EstimatorSpec, ...]
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    selection_metric: SelectionMetric = SelectionMetric.SPEARMAN_IC
    inner_validation_fraction: float = DEFAULT_INNER_VALIDATION_FRACTION
    early_stopping_rounds: int | None = None

    def __post_init__(self) -> None:
        if self.max_candidates < 1:
            msg = "max_candidates must be at least 1"
            raise PredictiveSpecError(msg)
        if self.max_candidates > MAX_CANDIDATES_CAP:
            msg = f"max_candidates must be <= {MAX_CANDIDATES_CAP}, got {self.max_candidates}"
            raise PredictiveSpecError(msg)
        if not self.candidates:
            msg = "candidate set must declare at least one candidate"
            raise PredictiveSpecError(msg)
        if len(self.candidates) > self.max_candidates:
            msg = (
                f"candidate set has {len(self.candidates)} candidates; "
                f"max_candidates is {self.max_candidates}"
            )
            raise PredictiveSpecError(msg)
        if not (0.0 < self.inner_validation_fraction <= 0.5):
            msg = (
                "inner_validation_fraction must be in (0, 0.5], "
                f"got {self.inner_validation_fraction}"
            )
            raise PredictiveSpecError(msg)
        if self.early_stopping_rounds is not None and (
            isinstance(self.early_stopping_rounds, bool)
            or not isinstance(self.early_stopping_rounds, int)
            or self.early_stopping_rounds < 1
        ):
            msg = "early_stopping_rounds must be a positive integer"
            raise PredictiveSpecError(msg)
        task_types = {candidate.task_type for candidate in self.candidates}
        if len(task_types) != 1:
            msg = "every candidate must share the same task_type"
            raise PredictiveSpecError(msg)
        expected = _METRIC_BY_TASK[next(iter(task_types))]
        if self.selection_metric is not expected:
            msg = (
                f"selection_metric {self.selection_metric.value} does not match "
                f"task_type {next(iter(task_types)).value}; expected {expected.value}"
            )
            raise PredictiveSpecError(msg)
        identities = [_candidate_identity(candidate) for candidate in self.candidates]
        duplicates = sorted({key for key in identities if identities.count(key) > 1})
        if duplicates:
            msg = f"candidate set contains duplicate candidates: {duplicates}"
            raise PredictiveSpecError(msg)

    @property
    def task_type(self) -> TaskType:
        return self.candidates[0].task_type

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "max_candidates": self.max_candidates,
            "selection_metric": self.selection_metric.value,
            "inner_validation_fraction": self.inner_validation_fraction,
        }
        if self.early_stopping_rounds is not None:
            payload["early_stopping_rounds"] = self.early_stopping_rounds
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateSetSpec:
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, (str, bytes)):
            msg = "candidate set candidates must be a sequence"
            raise PredictiveSpecError(msg)
        candidates = tuple(
            EstimatorSpec.from_dict(item) if isinstance(item, Mapping) else _reject_candidate()
            for item in raw_candidates
        )
        metric_raw = payload.get("selection_metric", SelectionMetric.SPEARMAN_IC.value)
        try:
            metric = SelectionMetric(str(metric_raw))
        except ValueError as exc:
            msg = f"invalid selection_metric: {metric_raw!r}"
            raise PredictiveSpecError(msg) from exc
        return cls(
            candidates=candidates,
            max_candidates=int(payload.get("max_candidates", DEFAULT_MAX_CANDIDATES)),
            selection_metric=metric,
            inner_validation_fraction=float(
                payload.get("inner_validation_fraction", DEFAULT_INNER_VALIDATION_FRACTION)
            ),
            early_stopping_rounds=_optional_positive_int(payload.get("early_stopping_rounds")),
        )


@dataclass(frozen=True, slots=True)
class CandidateFoldScore:
    """One candidate's inner-validation score inside one outer fold."""

    family: str
    hyperparameters: Mapping[str, Any]
    seed: int
    identity_hash: str
    inner_validation_score: float | None
    selected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "hyperparameters": dict(self.hyperparameters),
            "seed": self.seed,
            "identity_hash": self.identity_hash,
            "inner_validation_score": self.inner_validation_score,
            "selected": self.selected,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateFoldScore:
        hyperparameters = payload.get("hyperparameters", {})
        if not isinstance(hyperparameters, Mapping):
            msg = "candidate hyperparameters must be a mapping"
            raise PredictiveSpecError(msg)
        return cls(
            family=str(payload.get("family", "")),
            hyperparameters=dict(hyperparameters),
            seed=_require_int(payload.get("seed"), "seed"),
            identity_hash=str(payload.get("identity_hash", "")),
            inner_validation_score=_optional_float(payload.get("inner_validation_score")),
            selected=bool(payload.get("selected", False)),
        )


@dataclass(frozen=True, slots=True)
class FoldSelectionTrace:
    """Selection outcome for one outer walk-forward fold."""

    fold_id: int
    winner: EstimatorSpec
    candidates: tuple[CandidateFoldScore, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "winner": self.winner.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FoldSelectionTrace:
        winner_raw = payload.get("winner")
        if not isinstance(winner_raw, Mapping):
            msg = "selection winner must be a mapping"
            raise PredictiveSpecError(msg)
        candidates_raw = payload.get("candidates")
        if not isinstance(candidates_raw, Sequence) or isinstance(candidates_raw, (str, bytes)):
            msg = "selection candidates must be a sequence"
            raise PredictiveSpecError(msg)
        return cls(
            fold_id=_require_int(payload.get("fold_id"), "fold_id"),
            winner=EstimatorSpec.from_dict(winner_raw),
            candidates=tuple(
                CandidateFoldScore.from_dict(item)
                if isinstance(item, Mapping)
                else _reject_candidate_score()
                for item in candidates_raw
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionTrace:
    """Persisted candidate scores per outer fold (sidecar JSON)."""

    selection_metric: SelectionMetric
    inner_validation_fraction: float
    folds: tuple[FoldSelectionTrace, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_metric": self.selection_metric.value,
            "inner_validation_fraction": self.inner_validation_fraction,
            "folds": [fold.to_dict() for fold in self.folds],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SelectionTrace:
        metric_raw = payload.get("selection_metric", SelectionMetric.SPEARMAN_IC.value)
        try:
            metric = SelectionMetric(str(metric_raw))
        except ValueError as exc:
            msg = f"invalid selection_metric: {metric_raw!r}"
            raise PredictiveSpecError(msg) from exc
        folds_raw = payload.get("folds")
        if not isinstance(folds_raw, Sequence) or isinstance(folds_raw, (str, bytes)):
            msg = "selection folds must be a sequence"
            raise PredictiveSpecError(msg)
        return cls(
            selection_metric=metric,
            inner_validation_fraction=float(payload.get("inner_validation_fraction", 0.0)),
            folds=tuple(
                FoldSelectionTrace.from_dict(item)
                if isinstance(item, Mapping)
                else _reject_fold_trace()
                for item in folds_raw
            ),
        )


def split_inner_train_validation(
    n_rows: int,
    *,
    inner_validation_fraction: float = DEFAULT_INNER_VALIDATION_FRACTION,
    min_rows: int = MIN_INNER_SPLIT_ROWS,
) -> tuple[range, range]:
    """Split chronological TRAIN rows: prefix = inner train, suffix = inner val."""
    if n_rows < 1:
        msg = "inner split requires a non-empty TRAIN fold"
        raise PredictiveSpecError(msg)
    if not (0.0 < inner_validation_fraction <= 0.5):
        msg = f"inner_validation_fraction must be in (0, 0.5], got {inner_validation_fraction}"
        raise PredictiveSpecError(msg)
    n_validation = int(n_rows * inner_validation_fraction)
    n_train = n_rows - n_validation
    if n_train < min_rows or n_validation < min_rows:
        msg = (
            f"inner split needs at least {min_rows} inner-train and {min_rows} "
            f"inner-validation rows; TRAIN fold has {n_rows} rows "
            f"(fraction={inner_validation_fraction})"
        )
        raise PredictiveSpecError(msg)
    return range(0, n_train), range(n_train, n_rows)


def select_winning_index(scores: Sequence[float | None]) -> int:
    """Return the first index with the highest finite score (stable ties)."""
    if not scores:
        msg = "cannot select a winner from an empty score list"
        raise PredictiveSpecError(msg)
    best_index: int | None = None
    best_score = float("-inf")
    for index, score in enumerate(scores):
        if score is None:
            continue
        if score > best_score:
            best_score = score
            best_index = index
    if best_index is None:
        msg = "every candidate scored null on inner validation"
        raise PredictiveSpecError(msg)
    return best_index


def require_early_stopping_eval_roles(roles: Sequence[FoldRole]) -> None:
    """Reject early-stopping eval sets that include outer TEST or leak guards.

    Inner validation is a suffix of outer TRAIN rows, so permitted roles are
    TRAIN only. Passing TEST / PURGED / EMBARGOED is ``PredictiveSpecError``.
    """
    if not roles:
        msg = "early stopping eval set must be non-empty"
        raise PredictiveSpecError(msg)
    forbidden = {FoldRole.TEST, FoldRole.PURGED, FoldRole.EMBARGOED}
    offenders = sorted({role.value for role in roles if role in forbidden})
    if offenders:
        msg = f"early stopping cannot reference outer TEST or leak-guard rows; got {offenders}"
        raise PredictiveSpecError(msg)


def candidate_identity_hash(spec: EstimatorSpec) -> str:
    """Stable identity for uniqueness and the selection trace."""
    return _candidate_identity(spec)


def _candidate_identity(spec: EstimatorSpec) -> str:
    payload = {
        "family": spec.family,
        "hyperparameters": dict(spec.hyperparameters),
        "seed": spec.seed,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return canonical


def _reject_candidate() -> EstimatorSpec:
    msg = "each candidate must be a mapping"
    raise PredictiveSpecError(msg)


def _reject_candidate_score() -> CandidateFoldScore:
    msg = "each candidate score must be a mapping"
    raise PredictiveSpecError(msg)


def _reject_fold_trace() -> FoldSelectionTrace:
    msg = "each selection fold must be a mapping"
    raise PredictiveSpecError(msg)


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


def _optional_positive_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        msg = "early_stopping_rounds must be a positive integer"
        raise PredictiveSpecError(msg)
    return value
