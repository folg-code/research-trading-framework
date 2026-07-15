"""Tests for bounded model-family planning."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import (
    CandidateBounds,
    ModelFamilySpec,
    ModelFamilyVariant,
    SignalResearchDefinitionSpec,
)
from trading_framework.research.signal_research.family_planning import (
    ModelFamilyPlanningError,
    plan_model_family_experiment,
)


def _base_family_spec(*, max_candidates: int = 2) -> SignalResearchDefinitionSpec:
    return SignalResearchDefinitionSpec(
        research_id="signal_family_study",
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        dataset_ref=DatasetRef.parse("ES.c.0|ohlcv|1m|csv|test@1"),
        time_range=TimeRange(
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC),
        ),
        horizons=("5m",),
        candidate_bounds=CandidateBounds(max_candidates=max_candidates),
        model_family=ModelFamilySpec(
            family_id="canonical_signal_family",
            variants=(
                ModelFamilyVariant(
                    variant_id="higher_low",
                    signal_model_id="higher_low_long",
                ),
                ModelFamilyVariant(
                    variant_id="vol_edge",
                    signal_model_id="high_volatility_long_edge",
                ),
                ModelFamilyVariant(
                    variant_id="combined",
                    signal_model_id="high_vol_and_higher_low",
                ),
            ),
        ),
    )


def test_plan_model_family_respects_candidate_bounds() -> None:
    plan = plan_model_family_experiment(_base_family_spec(max_candidates=2))

    assert plan.candidates_generated == 3
    assert plan.candidates_evaluated == 2
    assert plan.candidates_skipped == 1
    assert plan.skipped_variant_ids == ("combined",)
    assert len(plan.candidates) == 2
    assert plan.candidates[0].variant_id == "higher_low"
    assert plan.candidates[0].spec.signal_model_id == "higher_low_long"
    assert plan.candidates[1].variant_id == "vol_edge"


def test_plan_model_family_requires_family_declaration() -> None:
    spec = SignalResearchDefinitionSpec(
        research_id="single_run",
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        dataset_ref=DatasetRef.parse("ES.c.0|ohlcv|1m|csv|test@1"),
        time_range=TimeRange(
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC),
        ),
        horizons=("5m",),
        signal_model_id="higher_low_long",
    )
    with pytest.raises(ModelFamilyPlanningError, match="model_family must be declared"):
        plan_model_family_experiment(spec)
