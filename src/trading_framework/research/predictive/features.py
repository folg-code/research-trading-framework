"""Declared feature contracts for Predictive Research (D-S039-07)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.research.predictive.errors import PredictiveSpecError


class FeatureTransform(StrEnum):
    """Bounded per-column transform applied after the analysis output is resolved."""

    NONE = "NONE"
    LOG = "LOG"
    DIFF = "DIFF"
    PCT_CHANGE = "PCT_CHANGE"
    RANK = "RANK"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """One declared analysis output used as a predictive feature.

    A feature is an ``AnalysisFrame`` column identity (component, parameters,
    output), not an arbitrary DataFrame name. The matrix builder maps this onto
    ``AnalysisFrameColumnSpec``; it must not recompute analysis.
    """

    component_id: ComponentId
    parameters: CanonicalParameters
    output_id: OutputId
    alias: str
    transform: FeatureTransform = FeatureTransform.NONE

    def __post_init__(self) -> None:
        normalized = self.alias.strip()
        if not normalized:
            msg = "feature alias must be non-empty"
            raise PredictiveSpecError(msg)
        if normalized != self.alias:
            object.__setattr__(self, "alias", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id.value,
            "parameters": self.parameters.to_json_dict(),
            "output_id": self.output_id.value,
            "alias": self.alias,
            "transform": self.transform.value,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FeatureSpec:
        raw_parameters = payload.get("parameters", {})
        if not isinstance(raw_parameters, dict):
            msg = "feature parameters must be a mapping"
            raise PredictiveSpecError(msg)
        raw_transform = payload.get("transform", FeatureTransform.NONE)
        try:
            transform = FeatureTransform(str(raw_transform))
        except ValueError as exc:
            msg = f"invalid feature transform: {raw_transform!r}"
            raise PredictiveSpecError(msg) from exc
        try:
            return cls(
                component_id=ComponentId(str(payload["component_id"])),
                parameters=CanonicalParameters.from_mapping(raw_parameters),
                output_id=OutputId(str(payload["output_id"])),
                alias=str(payload["alias"]),
                transform=transform,
            )
        except KeyError as exc:
            msg = f"feature spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        except ValidationError as exc:
            if isinstance(exc, PredictiveSpecError):
                raise
            raise PredictiveSpecError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class FeatureMatrixSpec:
    """Ordered, non-empty collection of declared features with unique aliases."""

    features: tuple[FeatureSpec, ...]

    def __post_init__(self) -> None:
        if not self.features:
            msg = "feature matrix must contain at least one feature"
            raise PredictiveSpecError(msg)
        aliases = [feature.alias for feature in self.features]
        if len(set(aliases)) != len(aliases):
            msg = "feature aliases must be unique"
            raise PredictiveSpecError(msg)

    def to_dict(self) -> list[dict[str, Any]]:
        return [feature.to_dict() for feature in self.features]

    @classmethod
    def from_dict(cls, payload: object) -> FeatureMatrixSpec:
        if not isinstance(payload, (list, tuple)):
            msg = "feature matrix must be a sequence of feature mappings"
            raise PredictiveSpecError(msg)
        features: list[FeatureSpec] = []
        for item in payload:
            if not isinstance(item, dict):
                msg = "each feature must be a mapping"
                raise PredictiveSpecError(msg)
            features.append(FeatureSpec.from_dict({str(key): value for key, value in item.items()}))
        return cls(features=tuple(features))
