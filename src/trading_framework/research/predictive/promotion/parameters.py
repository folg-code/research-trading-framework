"""The promoted-artifact parameter payload (ADR-0029 §1's ``artifact.json``).

This is the "other half" of a promoted artifact: the manifest
(``research/datasets/promoted_artifact.py``) carries identity, provenance and
declared shape (ordered feature ``OutputRef``s, ``model_family``,
``preprocessing_spec``, ``estimator_spec``); this module carries the actual
fitted numbers the evaluator needs to reproduce a prediction — coefficients,
intercept, and the fitted preprocessing statistics. No library object travels
here, only plain floats.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from trading_framework.research.predictive.errors import PromotedArtifactFormatError

#: The only format this evaluator understands (D-S049-06 / ADR-0029 §1).
#: Mirrors ``research.datasets.promoted_artifact``'s ``format="numpy_parameter_file"``
#: fixtures; duplicated here (rather than imported) because layering runs
#: research/predictive -> research/datasets, never the reverse (ADR-0029 §9).
PROMOTED_ARTIFACT_FORMAT = "numpy_parameter_file"

#: format_version values load_promoted_artifact accepts. Growing this set is a
#: format decision, not a call-site flag -- there is no bypass parameter.
SUPPORTED_FORMAT_VERSIONS = frozenset({"v1"})


@dataclass(frozen=True, slots=True)
class PromotedArtifactParameters:
    """The fitted numbers behind a promoted artifact (``artifact.json``).

    ``impute_median`` / ``standardize_mean`` / ``standardize_scale`` mirror
    ``FittedNumpyPreprocessor.statistics()`` / ``FittedSklearnPreprocessor.statistics()``
    exactly: optional, per-column, present only for the preprocessing steps
    that were actually fitted. ``coefficients`` is one weight per feature, in
    the same positional order as the manifest's ``feature_output_refs``.
    """

    coefficients: tuple[float, ...]
    intercept: float
    impute_median: tuple[float, ...] | None = None
    standardize_mean: tuple[float, ...] | None = None
    standardize_scale: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if not self.coefficients:
            msg = "coefficients must be non-empty"
            raise PromotedArtifactFormatError(msg)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "coefficients": list(self.coefficients),
            "intercept": self.intercept,
        }
        if self.impute_median is not None:
            payload["impute_median"] = list(self.impute_median)
        if self.standardize_mean is not None:
            payload["standardize_mean"] = list(self.standardize_mean)
        if self.standardize_scale is not None:
            payload["standardize_scale"] = list(self.standardize_scale)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PromotedArtifactParameters:
        for field in ("coefficients", "intercept"):
            if field not in payload:
                msg = f"promoted artifact payload missing required field: {field}"
                raise PromotedArtifactFormatError(msg)
        return cls(
            coefficients=_as_float_tuple(payload["coefficients"]),
            intercept=float(payload["intercept"]),
            impute_median=_optional_float_tuple(payload.get("impute_median")),
            standardize_mean=_optional_float_tuple(payload.get("standardize_mean")),
            standardize_scale=_optional_float_tuple(payload.get("standardize_scale")),
        )


def _as_float_tuple(values: Sequence[Any]) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


def _optional_float_tuple(values: Sequence[Any] | None) -> tuple[float, ...] | None:
    if values is None:
        return None
    return _as_float_tuple(values)
