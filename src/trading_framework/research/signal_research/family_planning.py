"""Plan bounded model-family candidates from a research definition."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.signal_research.definition import (
    ModelFamilySpec,
    ModelFamilyVariant,
    SignalResearchDefinitionSpec,
)


class ModelFamilyPlanningError(ValidationError):
    """Raised when a model family cannot be expanded into bounded candidates."""


@dataclass(frozen=True, slots=True)
class FamilyVariantCandidate:
    """One variant-specific definition ready for orchestration."""

    variant_id: str
    spec: SignalResearchDefinitionSpec


@dataclass(frozen=True, slots=True)
class FamilyExperimentPlan:
    """Bounded expansion of one declared model family."""

    experiment_id: str
    family_id: str
    candidates_generated: int
    candidates_evaluated: int
    candidates_skipped: int
    candidates: tuple[FamilyVariantCandidate, ...]
    skipped_variant_ids: tuple[str, ...]


def plan_model_family_experiment(
    spec: SignalResearchDefinitionSpec,
) -> FamilyExperimentPlan:
    """Expand a family definition into an ordered, capped candidate list."""
    family = spec.model_family
    if family is None:
        msg = "model_family must be declared to plan a family experiment"
        raise ModelFamilyPlanningError(msg)

    generated = len(family.variants)
    max_candidates = spec.candidate_bounds.max_candidates
    evaluated = min(generated, max_candidates)
    skipped_ids = tuple(variant.variant_id for variant in family.variants[evaluated:])

    candidates: list[FamilyVariantCandidate] = []
    for variant in family.variants[:evaluated]:
        candidates.append(
            FamilyVariantCandidate(
                variant_id=variant.variant_id,
                spec=_variant_spec(spec, family=family, variant=variant),
            )
        )

    return FamilyExperimentPlan(
        experiment_id=f"{spec.research_id}__{family.family_id}",
        family_id=family.family_id,
        candidates_generated=generated,
        candidates_evaluated=evaluated,
        candidates_skipped=generated - evaluated,
        candidates=tuple(candidates),
        skipped_variant_ids=skipped_ids,
    )


def _variant_spec(
    base: SignalResearchDefinitionSpec,
    *,
    family: ModelFamilySpec,
    variant: ModelFamilyVariant,
) -> SignalResearchDefinitionSpec:
    market_model_id = variant.market_model_id or base.market_model_id
    signal_model_id = variant.signal_model_id or base.signal_model_id
    return SignalResearchDefinitionSpec(
        research_id=f"{base.research_id}__{variant.variant_id}",
        research_scope=base.research_scope,
        dataset_ref=base.dataset_ref,
        time_range=base.time_range,
        horizons=base.horizons,
        research_question=base.research_question,
        market_model_id=market_model_id,
        signal_model_id=signal_model_id,
        evaluation_timeframe=base.evaluation_timeframe,
        baseline=base.baseline,
        grouping=base.grouping,
        occurrence_policy=base.occurrence_policy,
        quality_rules=base.quality_rules,
        candidate_bounds=base.candidate_bounds,
        model_family=None,
    )
