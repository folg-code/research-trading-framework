"""Preprocessing spec and TRAIN-only fit contract (D-S040-14)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.splitting import FoldRole


class PreprocessingStep(StrEnum):
    """Bounded per-fold transform. Do not grow this set in Sprint 040."""

    IMPUTE_MEDIAN = "IMPUTE_MEDIAN"
    STANDARDIZE = "STANDARDIZE"


def _default_steps() -> tuple[PreprocessingStep, ...]:
    return (PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)


@dataclass(frozen=True, slots=True)
class PreprocessingSpec:
    """Declared fold-local transforms applied before the estimator.

    Default pipeline is median imputation then standardization. The spec is
    hashed into run identity. Fitting is TRAIN-only and per fold: statistics
    computed on one fold's TRAIN rows must not be reused on another fold, and
    PURGED / EMBARGOED rows never reach ``fit()``. This type is the domain
    contract; the sklearn transform implementation lives in the adapter.
    """

    steps: tuple[PreprocessingStep, ...] = field(default_factory=_default_steps)

    def __post_init__(self) -> None:
        if not self.steps:
            msg = "preprocessing spec must declare at least one step"
            raise PredictiveSpecError(msg)
        if len(set(self.steps)) != len(self.steps):
            msg = "preprocessing steps must be unique"
            raise PredictiveSpecError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [step.value for step in self.steps]}

    def identity_payload(self) -> dict[str, Any]:
        """Canonical mapping hashed into future run identity."""
        return self.to_dict()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PreprocessingSpec:
        try:
            raw_steps = payload["steps"]
        except KeyError as exc:
            msg = f"preprocessing spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        if not isinstance(raw_steps, (list, tuple)):
            msg = "preprocessing steps must be a sequence"
            raise PredictiveSpecError(msg)
        steps: list[PreprocessingStep] = []
        for raw_step in raw_steps:
            try:
                steps.append(PreprocessingStep(str(raw_step)))
            except ValueError as exc:
                msg = f"invalid preprocessing step: {raw_step!r}"
                raise PredictiveSpecError(msg) from exc
        return cls(steps=tuple(steps))


def default_preprocessing_spec() -> PreprocessingSpec:
    """Return IMPUTE_MEDIAN then STANDARDIZE."""
    return PreprocessingSpec()


def require_train_only_fit_roles(fold_roles: Sequence[FoldRole]) -> None:
    """Reject any fold role that must not be passed to preprocessing or estimator fit.

    Fit is TRAIN-only and per-fold. TEST rows are prediction-only. PURGED and
    EMBARGOED rows never reach ``fit()``. A fitted transform is never reused
    across folds.
    """
    if not fold_roles:
        msg = "fit requires at least one TRAIN row"
        raise PredictiveSpecError(msg)
    forbidden = sorted({role.value for role in fold_roles if role is not FoldRole.TRAIN})
    if forbidden:
        msg = (
            "preprocessing and estimator fit accept TRAIN rows only; "
            f"forbidden fold roles: {forbidden}. "
            "PURGED and EMBARGOED rows never reach fit()"
        )
        raise PredictiveSpecError(msg)


def canonicalize_preprocessing_json(spec: PreprocessingSpec) -> str:
    """JSON-stable form of the spec for run-identity hashing."""
    return json.dumps(spec.identity_payload(), sort_keys=True, separators=(",", ":"))
