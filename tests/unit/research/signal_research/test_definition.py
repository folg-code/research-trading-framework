"""Unit tests for SignalResearchDefinitionSpec."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.application.signal_research.map_definition import (
    map_definition_to_analyze_request,
    map_definition_to_run_request,
    resolve_signal_research_definition,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.analytics.dimensions import GroupDimension
from trading_framework.research.datasets import RunDatasetRef
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import (
    BaselineType,
    OccurrencePolicyType,
    ResearchGroupingDimension,
    SignalResearchDefinitionError,
    SignalResearchDefinitionSpec,
    compute_definition_hash,
)
from trading_framework.research.signal_research.horizons import horizon_to_bars
from trading_framework.research.signal_research.loader import load_signal_research_definition
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef.parse("ES.c.0|ohlcv|1m|csv|test@1")


def _combined_spec() -> SignalResearchDefinitionSpec:
    return SignalResearchDefinitionSpec(
        research_id="combined_study",
        research_scope=ResearchScope.MARKET_AND_SIGNAL,
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        horizons=("5m", "15m"),
        market_model_id="high_volatility",
        signal_model_id="higher_low_long",
        baseline=BaselineType.SIGNAL_ONLY,
        grouping=(
            ResearchGroupingDimension.MONTH,
            ResearchGroupingDimension.SESSION,
            ResearchGroupingDimension.TIME_OF_DAY,
        ),
    )


def _time_range() -> TimeRange:
    return TimeRange(
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC),
    )


def test_horizon_to_bars_on_one_minute_base() -> None:
    assert horizon_to_bars("5m", evaluation_timeframe=Timeframe("1m")) == 5
    assert horizon_to_bars("1h", evaluation_timeframe=Timeframe("1m")) == 60


def test_definition_hash_is_stable_for_same_content() -> None:
    spec = _combined_spec()
    first = compute_definition_hash(spec)
    second = compute_definition_hash(spec)
    assert first == second
    assert len(first) == 64


def test_market_and_signal_requires_both_models() -> None:
    with pytest.raises(
        SignalResearchDefinitionError, match="requires market_model and signal_model"
    ):
        SignalResearchDefinitionSpec(
            research_id="invalid",
            research_scope=ResearchScope.MARKET_AND_SIGNAL,
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            horizons=("5m",),
            signal_model_id="higher_low_long",
        )


def test_signal_only_rejects_market_model() -> None:
    with pytest.raises(SignalResearchDefinitionError, match="must not declare market_model"):
        SignalResearchDefinitionSpec(
            research_id="invalid",
            research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            horizons=("5m",),
            market_model_id="high_volatility",
            signal_model_id="higher_low_long",
        )


def test_load_yaml_fixture() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "signal_research"
        / "nq_half_year_definition.yaml"
    )
    spec = load_signal_research_definition(fixture)
    assert spec.research_id == "nq_half_year_model_research"
    assert spec.research_scope is ResearchScope.MARKET_AND_SIGNAL
    assert spec.market_model_id == "high_volatility"
    assert spec.signal_model_id == "higher_low_long"
    assert spec.occurrence_policy.type is OccurrencePolicyType.COOLDOWN
    assert spec.occurrence_policy.duration == "15m"
    assert spec.baseline is BaselineType.SIGNAL_ONLY


def test_resolve_and_map_to_run_request(tmp_path: Path) -> None:
    resolved = resolve_signal_research_definition(_combined_spec())
    assert resolved.spec.definition_hash is not None
    assert resolved.horizon_bars == (5, 15)
    assert resolved.models.market_models[0].market_model_id == "high_volatility"
    assert resolved.models.signal_models[0].signal_model_id == "higher_low_long"

    run_request = map_definition_to_run_request(
        resolved,
        storage_root=tmp_path / "storage",
    )
    assert run_request.scope is ResearchScope.MARKET_AND_SIGNAL
    assert run_request.horizons == (5, 15)
    assert run_request.experiment_id == "combined_study"
    assert run_request.definition_hash == resolved.spec.definition_hash
    assert run_request.occurrence_policy == {"type": "KEEP_ALL"}


def test_map_to_analyze_request_sets_grouping_and_conditional_context(tmp_path: Path) -> None:
    resolved = resolve_signal_research_definition(_combined_spec())
    analyze_request = map_definition_to_analyze_request(
        resolved,
        run_ref=RunDatasetRef(run_id="abc123"),
        storage_root=tmp_path / "storage",
    )
    assert analyze_request.conditional_context is True
    assert analyze_request.group_by == (
        GroupDimension.CALENDAR_MONTH,
        GroupDimension.RTH_MEMBERSHIP,
        GroupDimension.TIME_OF_DAY,
    )
    assert analyze_request.interpretation_min_sample_size == 100


def test_definition_to_dict_round_trip() -> None:
    original = _combined_spec()
    restored = SignalResearchDefinitionSpec.from_dict(original.to_dict())
    assert restored.research_id == original.research_id
    assert restored.research_scope == original.research_scope
    assert restored.market_model_id == original.market_model_id
    assert restored.signal_model_id == original.signal_model_id
