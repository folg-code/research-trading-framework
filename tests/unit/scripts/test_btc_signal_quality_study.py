"""Smoke tests for Sprint 058 T005's worked-example scripts.

These scripts build a real dataset against the published BTCUSDT.P data
(gitignored, present only on the maintainer's machine, ADR-0002) -- these
tests cover the STRATEGY/SPEC COMPOSITION logic only (no network, no real
data, no ML extra), the same synthetic-only boundary every other script
test in this directory keeps to.
"""

from __future__ import annotations

from scripts.strategy_research import build_btc_signal_quality_study
from scripts.strategy_research._btc_rsi_relative_volatility import (
    STRATEGY_MODEL_ID,
    build_market_model,
    build_signal_model,
    build_strategy,
)

from trading_framework.research.predictive import PredictiveTask, SampleKind
from trading_framework.strategy import ScoreConditionSpec, validate_strategy_model_definition


def test_build_strategy_composes_a_valid_definition() -> None:
    strategy = build_strategy()

    validate_strategy_model_definition(strategy)
    assert strategy.strategy_model_id == STRATEGY_MODEL_ID
    assert strategy.score_condition is None


def test_build_strategy_with_score_condition_has_a_distinct_id() -> None:
    scored = build_strategy(
        score_condition=ScoreConditionSpec(artifact_fingerprint="a" * 64, threshold=0.5)
    )

    validate_strategy_model_definition(scored)
    assert scored.strategy_model_id != STRATEGY_MODEL_ID
    assert scored.score_condition is not None
    assert scored.score_condition.threshold == 0.5


def test_market_and_signal_model_are_independently_buildable() -> None:
    market = build_market_model()
    signal = build_signal_model()

    strategy = build_strategy()
    assert strategy.market_model.market_model_id == market.market_model_id
    assert strategy.signal_model.signal_model_id == signal.signal_model_id


def test_build_study_spec_declares_signal_quality_over_signal_occurrences() -> None:
    spec, signal_model = build_btc_signal_quality_study.build_study_spec()

    assert spec.task is PredictiveTask.SIGNAL_QUALITY
    assert spec.sample.kind is SampleKind.SIGNAL_OCCURRENCES
    assert spec.sample.signal_model_id == signal_model.signal_model_id
    assert spec.definition_hash is not None
    assert len(spec.features.features) == 10
