"""Unit tests for SampleSpec, PredictiveTask, and the sample x task compatibility matrix."""

from __future__ import annotations

import pytest

from trading_framework.research.predictive import (
    DEFAULT_SAMPLE_SPEC,
    IncompatibleSampleTaskError,
    PredictiveSpecError,
    PredictiveTask,
    ReservedPredictiveTaskError,
    ReservedSampleKindError,
    SampleDirection,
    SampleKind,
    SampleProvenance,
    SampleSpec,
    parse_predictive_task,
    parse_sample_kind,
    validate_sample_task_compatibility,
)


def test_default_sample_spec_is_every_bar_with_no_signal_model_fields() -> None:
    assert DEFAULT_SAMPLE_SPEC.kind is SampleKind.EVERY_BAR
    assert DEFAULT_SAMPLE_SPEC.signal_model_file is None
    assert DEFAULT_SAMPLE_SPEC.signal_model_id is None
    assert DEFAULT_SAMPLE_SPEC.direction is SampleDirection.ANY


def test_every_bar_sample_rejects_signal_model_fields() -> None:
    with pytest.raises(PredictiveSpecError, match="must not declare signal_model_file"):
        SampleSpec(kind=SampleKind.EVERY_BAR, signal_model_file="models/x.yaml")


def test_every_bar_sample_rejects_direction_filter() -> None:
    with pytest.raises(PredictiveSpecError, match="must not declare a direction filter"):
        SampleSpec(kind=SampleKind.EVERY_BAR, direction=SampleDirection.LONG)


def test_signal_occurrences_sample_requires_signal_model_file() -> None:
    with pytest.raises(PredictiveSpecError, match="requires signal_model_file"):
        SampleSpec(kind=SampleKind.SIGNAL_OCCURRENCES, signal_model_id="my_signal")


def test_signal_occurrences_sample_requires_signal_model_id() -> None:
    with pytest.raises(PredictiveSpecError, match="requires signal_model_id"):
        SampleSpec(kind=SampleKind.SIGNAL_OCCURRENCES, signal_model_file="models/x.yaml")


def test_signal_occurrences_sample_round_trips() -> None:
    sample = SampleSpec(
        kind=SampleKind.SIGNAL_OCCURRENCES,
        signal_model_file="models/breakout.yaml",
        signal_model_id="breakout_v1",
        direction=SampleDirection.LONG,
    )

    payload = sample.to_dict()
    restored = SampleSpec.from_dict(payload)

    assert restored == sample
    assert payload == {
        "kind": "signal_occurrences",
        "signal_model_file": "models/breakout.yaml",
        "signal_model_id": "breakout_v1",
        "direction": "LONG",
    }


def test_signal_occurrences_sample_omits_direction_when_any() -> None:
    sample = SampleSpec(
        kind=SampleKind.SIGNAL_OCCURRENCES,
        signal_model_file="models/breakout.yaml",
        signal_model_id="breakout_v1",
    )

    assert sample.to_dict() == {
        "kind": "signal_occurrences",
        "signal_model_file": "models/breakout.yaml",
        "signal_model_id": "breakout_v1",
    }


def test_every_bar_sample_to_dict_has_only_kind() -> None:
    assert SampleSpec(kind=SampleKind.EVERY_BAR).to_dict() == {"kind": "every_bar"}


@pytest.mark.parametrize(
    ("name", "owner"),
    [
        ("strategy_trades", "16F"),
        ("labelled_setups", "16F"),
        ("sessions_or_windows", "later, unassigned"),
    ],
)
def test_reserved_sample_kinds_are_refused_at_load_time(name: str, owner: str) -> None:
    with pytest.raises(ReservedSampleKindError, match=owner):
        parse_sample_kind(name)


def test_reserved_sample_kind_is_not_a_member_of_sample_kind() -> None:
    with pytest.raises(ValueError):
        SampleKind("strategy_trades")


def test_unknown_sample_kind_is_rejected_with_named_error() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown sample kind"):
        parse_sample_kind("bogus_kind")


@pytest.mark.parametrize(
    ("name", "owner"),
    [
        ("TRADE_OUTCOME", "16F"),
        ("NO_TRADE_FILTER", "16F"),
        ("REGIME_CLASSIFICATION", "later, unassigned"),
        ("VOLATILITY_FORECAST", "later, unassigned"),
        ("DISCRETIONARY_SETUP_CLASSIFICATION", "later, unassigned"),
    ],
)
def test_reserved_predictive_tasks_are_refused_at_load_time(name: str, owner: str) -> None:
    with pytest.raises(ReservedPredictiveTaskError, match=owner):
        parse_predictive_task(name)


def test_reserved_predictive_task_is_not_a_member_of_predictive_task() -> None:
    with pytest.raises(ValueError):
        PredictiveTask("TRADE_OUTCOME")


def test_unknown_predictive_task_is_rejected_with_named_error() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown predictive task"):
        parse_predictive_task("BOGUS_TASK")


def _signal_occurrences_sample() -> SampleSpec:
    return SampleSpec(
        kind=SampleKind.SIGNAL_OCCURRENCES,
        signal_model_file="models/breakout.yaml",
        signal_model_id="breakout_v1",
    )


def test_every_bar_forward_return_is_accepted() -> None:
    validate_sample_task_compatibility(DEFAULT_SAMPLE_SPEC, PredictiveTask.FORWARD_RETURN)


def test_signal_occurrences_forward_return_is_accepted() -> None:
    validate_sample_task_compatibility(_signal_occurrences_sample(), PredictiveTask.FORWARD_RETURN)


def test_signal_occurrences_signal_quality_is_accepted() -> None:
    validate_sample_task_compatibility(_signal_occurrences_sample(), PredictiveTask.SIGNAL_QUALITY)


def test_every_bar_signal_quality_is_refused() -> None:
    with pytest.raises(IncompatibleSampleTaskError, match="not compatible"):
        validate_sample_task_compatibility(DEFAULT_SAMPLE_SPEC, PredictiveTask.SIGNAL_QUALITY)


# --- SampleProvenance (S056-T003, ADR-0031 Decision 6) ----------------------
#
# `signal_occurrences` *resolution* (evaluate_models -> materialize_signal_
# occurrences -> a filtered row selection) is S056-T004, not this task, and
# does not exist yet. These tests therefore cover the every_bar path through
# the real manifest-writing code (tests/unit/research/datasets/
# test_predictive_repository.py and test_build_predictive_dataset.py), and
# cover the signal_occurrences *shape/contract* here with a manually
# constructed SampleProvenance — exactly the fixture-level coverage this
# task can honestly provide without T004's resolver.


def test_every_bar_provenance_records_the_whole_grid_explicitly() -> None:
    """An every_bar provenance states "whole grid used" via equal counts."""
    provenance = SampleProvenance(
        kind=SampleKind.EVERY_BAR,
        task=PredictiveTask.FORWARD_RETURN,
        universe_row_count=500,
        resolved_row_count=500,
        drop_counts={},
    )

    assert provenance.universe_row_count == provenance.resolved_row_count
    assert provenance.drop_counts == {}
    assert provenance.to_dict() == {
        "kind": "every_bar",
        "task": "FORWARD_RETURN",
        "universe_row_count": 500,
        "resolved_row_count": 500,
        "drop_counts": {},
    }


def test_signal_occurrences_provenance_round_trips_with_drop_reasons() -> None:
    """Contract-level coverage of the signal_occurrences shape (T004 resolves rows)."""
    provenance = SampleProvenance(
        kind=SampleKind.SIGNAL_OCCURRENCES,
        task=PredictiveTask.SIGNAL_QUALITY,
        universe_row_count=120,
        resolved_row_count=95,
        drop_counts={"incomplete_horizon": 17, "insufficient_data": 8},
    )

    payload = provenance.to_dict()
    restored = SampleProvenance.from_dict(payload)

    assert restored == provenance
    assert payload == {
        "kind": "signal_occurrences",
        "task": "SIGNAL_QUALITY",
        "universe_row_count": 120,
        "resolved_row_count": 95,
        "drop_counts": {"incomplete_horizon": 17, "insufficient_data": 8},
    }


def test_provenance_rejects_resolved_row_count_above_universe() -> None:
    with pytest.raises(PredictiveSpecError, match="cannot exceed universe_row_count"):
        SampleProvenance(
            kind=SampleKind.EVERY_BAR,
            task=PredictiveTask.FORWARD_RETURN,
            universe_row_count=10,
            resolved_row_count=11,
            drop_counts={},
        )


def test_provenance_rejects_drop_counts_that_do_not_sum_to_the_gap() -> None:
    with pytest.raises(PredictiveSpecError, match="drop_counts must sum to"):
        SampleProvenance(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            task=PredictiveTask.FORWARD_RETURN,
            universe_row_count=100,
            resolved_row_count=80,
            drop_counts={"incomplete_horizon": 5},
        )


def test_provenance_rejects_negative_universe_row_count() -> None:
    with pytest.raises(PredictiveSpecError, match="non-negative"):
        SampleProvenance(
            kind=SampleKind.EVERY_BAR,
            task=PredictiveTask.FORWARD_RETURN,
            universe_row_count=-1,
            resolved_row_count=0,
            drop_counts={},
        )


def test_provenance_rejects_negative_drop_count() -> None:
    with pytest.raises(PredictiveSpecError, match="drop count for 'incomplete_horizon'"):
        SampleProvenance(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            task=PredictiveTask.FORWARD_RETURN,
            universe_row_count=10,
            resolved_row_count=5,
            drop_counts={"incomplete_horizon": -5},
        )
