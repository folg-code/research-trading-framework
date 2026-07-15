"""Signal Research definition specification contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, assert_never

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.scope import ResearchScope
from trading_framework.time.models.timeframe import Timeframe


class OccurrencePolicyType(StrEnum):
    """Overlap handling policy for signal occurrences."""

    KEEP_ALL = "KEEP_ALL"
    FIRST_PER_BAR = "FIRST_PER_BAR"
    COOLDOWN = "COOLDOWN"


class BaselineType(StrEnum):
    """Scope-appropriate baseline comparison selector."""

    MODEL_ACTIVE = "MODEL_ACTIVE"
    AFTER_SIGNAL = "AFTER_SIGNAL"
    SIGNAL_ONLY = "SIGNAL_ONLY"


class ResearchGroupingDimension(StrEnum):
    """Declared grouping dimensions for analytics and reporting."""

    MONTH = "month"
    SESSION = "session"
    TIME_OF_DAY = "time_of_day"


class SignalResearchDefinitionError(ValidationError):
    """Raised when a research definition fails validation."""


@dataclass(frozen=True, slots=True)
class OccurrencePolicy:
    """How overlapping detections are treated for sample accounting."""

    type: OccurrencePolicyType
    duration: str | None = None

    def __post_init__(self) -> None:
        if self.type is OccurrencePolicyType.COOLDOWN:
            if self.duration is None or not self.duration.strip():
                msg = "COOLDOWN occurrence_policy requires duration"
                raise SignalResearchDefinitionError(msg)
            Timeframe(self.duration.strip())
            return
        if self.duration is not None:
            msg = f"duration is only valid for COOLDOWN, not {self.type.value}"
            raise SignalResearchDefinitionError(msg)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type.value}
        if self.duration is not None:
            payload["duration"] = self.duration
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> OccurrencePolicy:
        return cls(
            type=OccurrencePolicyType(str(payload["type"])),
            duration=(str(payload["duration"]) if payload.get("duration") is not None else None),
        )


@dataclass(frozen=True, slots=True)
class SignalResearchQualityRules:
    """Configurable diagnostic thresholds — warnings only."""

    minimum_sample_size: int = 100
    maximum_single_period_contribution: float = 0.40
    minimum_positive_period_share: float = 0.60
    maximum_incomplete_outcome_share: float = 0.05

    def __post_init__(self) -> None:
        if self.minimum_sample_size < 1:
            msg = "minimum_sample_size must be at least 1"
            raise SignalResearchDefinitionError(msg)
        if not 0.0 < self.maximum_single_period_contribution <= 1.0:
            msg = "maximum_single_period_contribution must be in (0, 1]"
            raise SignalResearchDefinitionError(msg)
        if not 0.0 <= self.minimum_positive_period_share <= 1.0:
            msg = "minimum_positive_period_share must be in [0, 1]"
            raise SignalResearchDefinitionError(msg)
        if not 0.0 <= self.maximum_incomplete_outcome_share <= 1.0:
            msg = "maximum_incomplete_outcome_share must be in [0, 1]"
            raise SignalResearchDefinitionError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum_sample_size": self.minimum_sample_size,
            "maximum_single_period_contribution": self.maximum_single_period_contribution,
            "minimum_positive_period_share": self.minimum_positive_period_share,
            "maximum_incomplete_outcome_share": self.maximum_incomplete_outcome_share,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SignalResearchQualityRules:
        return cls(
            minimum_sample_size=int(payload.get("minimum_sample_size", 100)),
            maximum_single_period_contribution=float(
                payload.get("maximum_single_period_contribution", 0.40)
            ),
            minimum_positive_period_share=float(payload.get("minimum_positive_period_share", 0.60)),
            maximum_incomplete_outcome_share=float(
                payload.get("maximum_incomplete_outcome_share", 0.05)
            ),
        )


@dataclass(frozen=True, slots=True)
class CandidateBounds:
    """Explicit cap on generated and evaluated research candidates."""

    max_candidates: int = 1

    def __post_init__(self) -> None:
        if self.max_candidates < 1:
            msg = "max_candidates must be at least 1"
            raise SignalResearchDefinitionError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {"max_candidates": self.max_candidates}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CandidateBounds:
        return cls(max_candidates=int(payload.get("max_candidates", 1)))


@dataclass(frozen=True, slots=True)
class ModelFamilyVariant:
    """One manually declared variant inside a model family."""

    variant_id: str
    market_model_id: str | None = None
    signal_model_id: str | None = None

    def __post_init__(self) -> None:
        normalized = self.variant_id.strip()
        if not normalized:
            msg = "model family variant_id must be non-empty"
            raise SignalResearchDefinitionError(msg)
        object.__setattr__(self, "variant_id", normalized)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.variant_id}
        if self.market_model_id is not None:
            payload["market_model"] = self.market_model_id
        if self.signal_model_id is not None:
            payload["signal_model"] = self.signal_model_id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ModelFamilyVariant:
        variant_id = str(payload.get("id") or payload["variant_id"])
        market_model = payload.get("market_model")
        signal_model = payload.get("signal_model")
        return cls(
            variant_id=variant_id,
            market_model_id=str(market_model) if market_model is not None else None,
            signal_model_id=str(signal_model) if signal_model is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ModelFamilySpec:
    """Ordered list of bounded model variants for comparison."""

    family_id: str
    variants: tuple[ModelFamilyVariant, ...]

    def __post_init__(self) -> None:
        normalized = self.family_id.strip()
        if not normalized:
            msg = "model_family id must be non-empty"
            raise SignalResearchDefinitionError(msg)
        object.__setattr__(self, "family_id", normalized)
        if not self.variants:
            msg = "model_family variants must contain at least one entry"
            raise SignalResearchDefinitionError(msg)
        variant_ids = [variant.variant_id for variant in self.variants]
        if len(set(variant_ids)) != len(variant_ids):
            msg = "model_family variant ids must be unique"
            raise SignalResearchDefinitionError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.family_id,
            "variants": [variant.to_dict() for variant in self.variants],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ModelFamilySpec:
        family_id = str(payload.get("id") or payload["family_id"])
        variants_payload = payload.get("variants", ())
        variants = tuple(ModelFamilyVariant.from_dict(item) for item in variants_payload)
        return cls(family_id=family_id, variants=variants)


@dataclass(frozen=True, slots=True)
class SignalResearchDefinitionSpec:
    """Declarative study contract for one bounded Signal Research run."""

    research_id: str
    research_scope: ResearchScope
    dataset_ref: DatasetRef
    time_range: TimeRange
    horizons: tuple[str, ...]
    research_question: str | None = None
    market_model_id: str | None = None
    signal_model_id: str | None = None
    evaluation_timeframe: Timeframe = field(default_factory=lambda: Timeframe("1m"))
    baseline: BaselineType | None = None
    grouping: tuple[ResearchGroupingDimension, ...] = ()
    occurrence_policy: OccurrencePolicy = field(
        default_factory=lambda: OccurrencePolicy(type=OccurrencePolicyType.KEEP_ALL)
    )
    quality_rules: SignalResearchQualityRules = field(default_factory=SignalResearchQualityRules)
    candidate_bounds: CandidateBounds = field(default_factory=CandidateBounds)
    model_family: ModelFamilySpec | None = None
    resolved_parameters: dict[str, Any] = field(default_factory=dict)
    component_lineage_hashes: dict[str, str] = field(default_factory=dict)
    definition_hash: str | None = None

    def __post_init__(self) -> None:
        normalized_id = self.research_id.strip()
        if not normalized_id:
            msg = "research_id must be non-empty"
            raise SignalResearchDefinitionError(msg)
        object.__setattr__(self, "research_id", normalized_id)
        if not self.horizons:
            msg = "horizons must contain at least one value"
            raise SignalResearchDefinitionError(msg)
        validate_signal_research_definition(self)

    def with_resolution(
        self,
        *,
        resolved_parameters: dict[str, Any],
        component_lineage_hashes: dict[str, str],
    ) -> SignalResearchDefinitionSpec:
        """Return a copy with resolved model metadata and computed definition hash."""
        resolved = SignalResearchDefinitionSpec(
            research_id=self.research_id,
            research_scope=self.research_scope,
            dataset_ref=self.dataset_ref,
            time_range=self.time_range,
            horizons=self.horizons,
            research_question=self.research_question,
            market_model_id=self.market_model_id,
            signal_model_id=self.signal_model_id,
            evaluation_timeframe=self.evaluation_timeframe,
            baseline=self.baseline,
            grouping=self.grouping,
            occurrence_policy=self.occurrence_policy,
            quality_rules=self.quality_rules,
            candidate_bounds=self.candidate_bounds,
            model_family=self.model_family,
            resolved_parameters=resolved_parameters,
            component_lineage_hashes=component_lineage_hashes,
            definition_hash=None,
        )
        object.__setattr__(
            resolved,
            "definition_hash",
            compute_definition_hash(resolved),
        )
        return resolved

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "research_id": self.research_id,
            "research_scope": self.research_scope.value,
            "dataset_ref": {
                "dataset_id": self.dataset_ref.dataset_id.canonical(),
                "version": self.dataset_ref.version,
            },
            "time_range": {
                "start": self.time_range.start.isoformat(),
                "end": self.time_range.end.isoformat(),
            },
            "horizons": list(self.horizons),
            "evaluation_timeframe": self.evaluation_timeframe.value,
            "occurrence_policy": self.occurrence_policy.to_dict(),
            "quality_rules": self.quality_rules.to_dict(),
            "candidate_bounds": self.candidate_bounds.to_dict(),
        }
        if self.model_family is not None:
            payload["model_family"] = self.model_family.to_dict()
        if self.research_question is not None:
            payload["research_question"] = self.research_question
        if self.market_model_id is not None:
            payload["market_model"] = self.market_model_id
        if self.signal_model_id is not None:
            payload["signal_model"] = self.signal_model_id
        if self.baseline is not None:
            payload["baseline"] = {"type": self.baseline.value}
        if self.grouping:
            payload["grouping"] = [dimension.value for dimension in self.grouping]
        if self.resolved_parameters:
            payload["resolved_parameters"] = self.resolved_parameters
        if self.component_lineage_hashes:
            payload["component_lineage_hashes"] = self.component_lineage_hashes
        if self.definition_hash is not None:
            payload["definition_hash"] = self.definition_hash
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SignalResearchDefinitionSpec:
        normalized = _normalize_definition_payload(payload)
        dataset_payload = normalized["dataset_ref"]
        if isinstance(dataset_payload, dict):
            dataset_ref = DatasetRef.parse(
                f"{dataset_payload['dataset_id']}@{dataset_payload['version']}"
            )
        else:
            dataset_ref = DatasetRef.parse(str(dataset_payload))

        time_payload = normalized["time_range"]
        time_range = TimeRange(
            start=_parse_datetime(time_payload["start"]),
            end=_parse_datetime(time_payload["end"], end_of_day=True),
        )

        baseline = None
        baseline_payload = normalized.get("baseline")
        if baseline_payload is not None:
            baseline_type = (
                baseline_payload["type"] if isinstance(baseline_payload, dict) else baseline_payload
            )
            baseline = BaselineType(str(baseline_type))

        grouping_raw = normalized.get("grouping", ())
        grouping = tuple(ResearchGroupingDimension(str(value)) for value in grouping_raw)

        occurrence_payload = normalized.get("occurrence_policy")
        occurrence_policy = (
            OccurrencePolicy.from_dict(occurrence_payload)
            if occurrence_payload is not None
            else OccurrencePolicy(type=OccurrencePolicyType.KEEP_ALL)
        )

        quality_payload = normalized.get("quality_rules")
        quality_rules = (
            SignalResearchQualityRules.from_dict(quality_payload)
            if quality_payload is not None
            else SignalResearchQualityRules()
        )

        bounds_payload = normalized.get("candidate_bounds")
        candidate_bounds = (
            CandidateBounds.from_dict(bounds_payload)
            if bounds_payload is not None
            else CandidateBounds()
        )

        family_payload = normalized.get("model_family")
        model_family = (
            ModelFamilySpec.from_dict(family_payload) if family_payload is not None else None
        )

        return cls(
            research_id=str(normalized.get("id") or normalized["research_id"]),
            research_scope=_parse_research_scope(
                str(normalized.get("scope") or normalized["research_scope"])
            ),
            dataset_ref=dataset_ref,
            time_range=time_range,
            horizons=tuple(str(value) for value in normalized["horizons"]),
            research_question=(
                str(normalized["research_question"])
                if normalized.get("research_question") is not None
                else None
            ),
            market_model_id=(
                str(normalized["market_model"])
                if normalized.get("market_model") is not None
                else None
            ),
            signal_model_id=(
                str(normalized["signal_model"])
                if normalized.get("signal_model") is not None
                else None
            ),
            evaluation_timeframe=Timeframe(str(normalized.get("evaluation_timeframe", "1m"))),
            baseline=baseline,
            grouping=grouping,
            occurrence_policy=occurrence_policy,
            quality_rules=quality_rules,
            candidate_bounds=candidate_bounds,
            model_family=model_family,
            resolved_parameters=dict(normalized.get("resolved_parameters", {})),
            component_lineage_hashes=dict(normalized.get("component_lineage_hashes", {})),
            definition_hash=(
                str(normalized["definition_hash"])
                if normalized.get("definition_hash") is not None
                else None
            ),
        )


def validate_signal_research_definition(spec: SignalResearchDefinitionSpec) -> None:
    """Validate scope, models, baseline, candidate bounds and model families."""
    if spec.model_family is not None:
        _validate_model_family(spec)
        return

    scope = spec.research_scope
    market_id = spec.market_model_id
    signal_id = spec.signal_model_id

    if scope is ResearchScope.SIGNAL_MODEL_ONLY:
        if market_id is not None:
            msg = "SIGNAL_MODEL_ONLY must not declare market_model"
            raise SignalResearchDefinitionError(msg)
        if signal_id is None:
            msg = "SIGNAL_MODEL_ONLY requires signal_model"
            raise SignalResearchDefinitionError(msg)
        _validate_baseline(scope, spec.baseline)
        return

    if scope is ResearchScope.MARKET_MODEL_ONLY:
        if signal_id is not None:
            msg = "MARKET_MODEL_ONLY must not declare signal_model"
            raise SignalResearchDefinitionError(msg)
        if market_id is None:
            msg = "MARKET_MODEL_ONLY requires market_model"
            raise SignalResearchDefinitionError(msg)
        _validate_baseline(scope, spec.baseline)
        return

    if scope is ResearchScope.MARKET_AND_SIGNAL:
        if market_id is None or signal_id is None:
            msg = "MARKET_AND_SIGNAL requires market_model and signal_model"
            raise SignalResearchDefinitionError(msg)
        _validate_baseline(scope, spec.baseline)
        return

    assert_never(scope)


def _validate_model_family(spec: SignalResearchDefinitionSpec) -> None:
    family = spec.model_family
    if family is None:
        return

    scope = spec.research_scope
    for variant in family.variants:
        market_model_id = variant.market_model_id or spec.market_model_id
        signal_model_id = variant.signal_model_id or spec.signal_model_id
        if scope is ResearchScope.SIGNAL_MODEL_ONLY:
            if market_model_id is not None:
                msg = (
                    f"variant {variant.variant_id!r} must not declare market_model "
                    "for SIGNAL_MODEL_ONLY"
                )
                raise SignalResearchDefinitionError(msg)
            if signal_model_id is None:
                msg = f"variant {variant.variant_id!r} requires signal_model"
                raise SignalResearchDefinitionError(msg)
        elif scope is ResearchScope.MARKET_MODEL_ONLY:
            if signal_model_id is not None:
                msg = (
                    f"variant {variant.variant_id!r} must not declare signal_model "
                    "for MARKET_MODEL_ONLY"
                )
                raise SignalResearchDefinitionError(msg)
            if market_model_id is None:
                msg = f"variant {variant.variant_id!r} requires market_model"
                raise SignalResearchDefinitionError(msg)
        elif scope is ResearchScope.MARKET_AND_SIGNAL:
            if market_model_id is None or signal_model_id is None:
                msg = (
                    f"variant {variant.variant_id!r} requires market_model and signal_model "
                    "for MARKET_AND_SIGNAL"
                )
                raise SignalResearchDefinitionError(msg)
        else:
            assert_never(scope)

    _validate_baseline(scope, spec.baseline)


def _validate_baseline(scope: ResearchScope, baseline: BaselineType | None) -> None:
    if baseline is None:
        return
    if scope is ResearchScope.MARKET_MODEL_ONLY and baseline is not BaselineType.MODEL_ACTIVE:
        msg = "MARKET_MODEL_ONLY baseline must be MODEL_ACTIVE"
        raise SignalResearchDefinitionError(msg)
    if scope is ResearchScope.SIGNAL_MODEL_ONLY and baseline is not BaselineType.AFTER_SIGNAL:
        msg = "SIGNAL_MODEL_ONLY baseline must be AFTER_SIGNAL"
        raise SignalResearchDefinitionError(msg)
    if scope is ResearchScope.MARKET_AND_SIGNAL and baseline is not BaselineType.SIGNAL_ONLY:
        msg = "MARKET_AND_SIGNAL baseline must be SIGNAL_ONLY"
        raise SignalResearchDefinitionError(msg)


def compute_definition_hash(spec: SignalResearchDefinitionSpec) -> str:
    """Fingerprint the normalized definition independent of run identity."""
    payload = spec.to_dict()
    payload.pop("definition_hash", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_research_scope(value: str) -> ResearchScope:
    normalized = value.strip()
    aliases = {
        "SIGNAL_MODEL_ONLY": ResearchScope.SIGNAL_MODEL_ONLY,
        "MARKET_MODEL_ONLY": ResearchScope.MARKET_MODEL_ONLY,
        "MARKET_AND_SIGNAL": ResearchScope.MARKET_AND_SIGNAL,
    }
    if normalized in aliases:
        return aliases[normalized]
    return ResearchScope(normalized)


def _normalize_definition_payload(payload: dict[str, Any]) -> dict[str, Any]:
    research_payload = payload.get("research")
    if isinstance(research_payload, dict):
        return research_payload
    return payload


def _parse_datetime(value: str, *, end_of_day: bool = False) -> datetime:
    text = str(value).strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        year, month, day = (int(part) for part in text.split("-"))
        if end_of_day:
            return datetime(year, month, day, 23, 59, 59, tzinfo=UTC)
        return datetime(year, month, day, tzinfo=UTC)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
