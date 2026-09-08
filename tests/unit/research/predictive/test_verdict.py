"""Unit tests for the Analyst Verdict Artifact vocabulary and rule set (ADR-0032)."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from trading_framework.research.predictive import (
    VERDICT_RULES_V1,
    RuleEvaluation,
    RunVerdict,
    TaskType,
    VerdictFacts,
    VerdictReport,
    evaluate_verdict,
)

_DEFAULT_ROLE_COUNTS = {"TRAIN": 500, "TEST": 300, "PURGED": 10, "EMBARGOED": 5}
_DEFAULT_EMBARGO = timedelta(days=1)
_DEFAULT_HORIZON = timedelta(hours=1)


def _clean_facts(**overrides: object) -> VerdictFacts:
    """A baseline REGRESSION fixture that fires no rejection rule and reaches O1 (PASS)."""
    defaults: dict[str, object] = {
        "task_type": TaskType.REGRESSION,
        "pooled_model_primary": 0.05,
        "pooled_random_permutation_primary": 0.01,
        "fold_model_primary": {"1": 0.06, "2": 0.05, "3": 0.04},
        "fold_random_permutation_primary": {"1": 0.01, "2": 0.0, "3": 0.02},
        "fold_train_primary": {"1": 0.05, "2": 0.05, "3": 0.05},
        "fold_test_primary": {"1": 0.05, "2": 0.05, "3": 0.05},
        "fold_test_row_counts": {"1": 100, "2": 100, "3": 100},
        "fold_count": 3,
        "role_counts": dict(_DEFAULT_ROLE_COUNTS),
        "embargo_span": _DEFAULT_EMBARGO,
        "label_horizon": _DEFAULT_HORIZON,
        "minority_class_share": None,
    }
    defaults.update(overrides)
    return VerdictFacts(**defaults)  # type: ignore[arg-type]


def _evaluation(report: VerdictReport, rule_id: str) -> RuleEvaluation:
    matches = [evaluation for evaluation in report.evaluations if evaluation.rule_id == rule_id]
    assert len(matches) == 1, f"expected exactly one {rule_id} evaluation"
    return matches[0]


# ---------------------------------------------------------------------------
# Every one of the eight vocabulary values is reachable.
# ---------------------------------------------------------------------------


def test_clean_run_produces_pass() -> None:
    report = evaluate_verdict(_clean_facts(), VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.PASS
    assert len(report.evaluations) == 8
    assert _evaluation(report, "O1").fired is True


def test_two_of_three_folds_winning_produces_weak_pass() -> None:
    facts = _clean_facts(
        fold_model_primary={"1": 0.06, "2": 0.05, "3": 0.01},
        fold_random_permutation_primary={"1": 0.01, "2": 0.0, "3": 0.02},
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.WEAK_PASS
    assert _evaluation(report, "O2").fired is True


def test_fewer_than_two_thirds_folds_winning_produces_inconclusive() -> None:
    # 4 folds, 2 wins (0.5 < 2/3), and wins != 1 so R4(b) does not also fire.
    facts = _clean_facts(
        fold_model_primary={"1": 0.06, "2": 0.06, "3": 0.001, "4": 0.001},
        fold_random_permutation_primary={"1": 0.01, "2": 0.01, "3": 0.05, "4": 0.05},
        fold_train_primary={"1": 0.05, "2": 0.05, "3": 0.05, "4": 0.05},
        fold_test_primary={"1": 0.05, "2": 0.05, "3": 0.05, "4": 0.05},
        fold_test_row_counts={"1": 100, "2": 100, "3": 100, "4": 100},
        fold_count=4,
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.INCONCLUSIVE
    assert _evaluation(report, "O3").fired is True
    assert _evaluation(report, "R4").fired is False


def test_non_positive_baseline_delta_produces_fail() -> None:
    facts = _clean_facts(
        pooled_model_primary=0.01,
        pooled_random_permutation_primary=0.02,
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.FAIL
    assert _evaluation(report, "O4").fired is True


def test_unanimous_gap_exceeding_pooled_effect_size_produces_rejected_overfit() -> None:
    # Sprint 052's real tree run: per-fold gaps 0.027-0.147 dwarf the pooled
    # effect size (0.024) -- ADR-0032's central worked example for R1.
    facts = _clean_facts(
        pooled_model_primary=0.024,
        pooled_random_permutation_primary=-0.005,
        fold_train_primary={"1": 0.1, "2": 0.15, "3": 0.2},
        fold_test_primary={"1": 0.073, "2": 0.1, "3": 0.053},
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_OVERFIT
    r1 = _evaluation(report, "R1")
    assert r1.fired is True
    assert r1.observed["unanimous_train_gt_test"] is True


def test_embargo_shorter_than_label_horizon_produces_rejected_leakage_risk() -> None:
    facts = _clean_facts(embargo_span=timedelta(minutes=30), label_horizon=timedelta(hours=1))

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LEAKAGE_RISK
    assert _evaluation(report, "R2").fired is True


def test_inactive_guards_with_positive_horizon_produces_rejected_leakage_risk() -> None:
    facts = _clean_facts(role_counts={"TRAIN": 500, "TEST": 300, "PURGED": 0, "EMBARGOED": 0})

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LEAKAGE_RISK


def test_implausible_pooled_effect_produces_rejected_leakage_risk() -> None:
    facts = _clean_facts(
        task_type=TaskType.CLASSIFICATION,
        pooled_model_primary=0.80,
        pooled_random_permutation_primary=0.50,
        minority_class_share=0.40,
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LEAKAGE_RISK


def test_small_fold_produces_rejected_low_sample() -> None:
    facts = _clean_facts(fold_test_row_counts={"1": 10, "2": 100, "3": 100})

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LOW_SAMPLE
    assert _evaluation(report, "R3").fired is True


def test_too_few_folds_produces_rejected_low_sample() -> None:
    facts = _clean_facts(
        fold_model_primary={"1": 0.06, "2": 0.05},
        fold_random_permutation_primary={"1": 0.01, "2": 0.0},
        fold_train_primary={"1": 0.05, "2": 0.05},
        fold_test_primary={"1": 0.05, "2": 0.05},
        fold_test_row_counts={"1": 100, "2": 100},
        fold_count=2,
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LOW_SAMPLE


def test_thin_minority_class_produces_rejected_low_sample() -> None:
    facts = _clean_facts(task_type=TaskType.CLASSIFICATION, minority_class_share=0.05)

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_LOW_SAMPLE


def test_single_fold_concentration_produces_rejected_concentration() -> None:
    facts = _clean_facts(fold_test_row_counts={"1": 700, "2": 100, "3": 100})

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_CONCENTRATION
    assert _evaluation(report, "R4").fired is True


def test_single_winning_fold_produces_rejected_concentration() -> None:
    facts = _clean_facts(
        fold_model_primary={"1": 0.06, "2": 0.001, "3": 0.001},
        fold_random_permutation_primary={"1": 0.01, "2": 0.05, "3": 0.05},
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.REJECTED_CONCENTRATION


# ---------------------------------------------------------------------------
# Rejection precedence: two rejection rules fire at once; the earlier wins,
# but both are recorded.
# ---------------------------------------------------------------------------


def test_two_simultaneous_rejections_record_both_but_earlier_wins() -> None:
    facts = _clean_facts(
        embargo_span=timedelta(minutes=30),  # R2(a) fires
        fold_test_row_counts={"1": 10, "2": 100, "3": 100},  # R3(a) fires
    )

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    r2 = _evaluation(report, "R2")
    r3 = _evaluation(report, "R3")
    assert r2.fired is True
    assert r3.fired is True
    # R2 precedes R3 in the fixed rule order (R2, R3, R4, R1).
    assert report.verdict is RunVerdict.REJECTED_LEAKAGE_RISK


# ---------------------------------------------------------------------------
# Missing required fact -> INCONCLUSIVE naming the missing input.
# ---------------------------------------------------------------------------


def test_missing_fold_primary_yields_inconclusive_naming_missing_input() -> None:
    # Otherwise a clean PASS-shaped run, but fold_primary (train/test per-fold
    # primary metrics) is absent -- the realistic case (ADR-0032 §2).
    facts = _clean_facts(fold_train_primary={}, fold_test_primary={})

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.INCONCLUSIVE
    r1 = _evaluation(report, "R1")
    assert r1.evaluated is False
    assert r1.fired is False
    assert r1.missing_input is not None
    assert "fold_primary" in r1.missing_input


def test_missing_pooled_random_permutation_yields_inconclusive() -> None:
    facts = _clean_facts(pooled_random_permutation_primary=None)

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.INCONCLUSIVE
    for rule_id in ("O1", "O2", "O3", "O4"):
        evaluation = _evaluation(report, rule_id)
        assert evaluation.evaluated is False
        assert evaluation.fired is False
        assert evaluation.missing_input is not None


def test_missing_input_never_produces_pass() -> None:
    """A missing fact must never be silently skipped in a way that yields PASS."""
    facts = _clean_facts(fold_train_primary={}, fold_test_primary={})

    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is not RunVerdict.PASS
    assert report.verdict is RunVerdict.INCONCLUSIVE


# ---------------------------------------------------------------------------
# Purity / determinism / round-trip.
# ---------------------------------------------------------------------------


def test_evaluate_verdict_is_pure_and_deterministic() -> None:
    facts = _clean_facts()

    first = evaluate_verdict(facts, VERDICT_RULES_V1)
    second = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert first.to_dict() == second.to_dict()
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(
        second.to_dict(), sort_keys=True
    )


def test_verdict_report_round_trips_through_dict() -> None:
    facts = _clean_facts()
    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    restored = VerdictReport.from_dict(report.to_dict())

    assert restored == report
    assert restored.to_dict() == report.to_dict()


@pytest.mark.parametrize(
    "facts",
    [
        _clean_facts(),
        _clean_facts(
            fold_model_primary={"1": 0.06, "2": 0.05, "3": 0.01},
            fold_random_permutation_primary={"1": 0.01, "2": 0.0, "3": 0.02},
        ),
        _clean_facts(embargo_span=timedelta(minutes=30)),
        _clean_facts(fold_train_primary={}, fold_test_primary={}),
    ],
)
def test_verdict_report_never_carries_a_wall_clock_field(facts: VerdictFacts) -> None:
    report = evaluate_verdict(facts, VERDICT_RULES_V1)
    payload = report.to_dict()

    serialized = json.dumps(payload)
    assert "created_at" not in serialized
    assert "duration" not in serialized
    assert "timestamp" not in serialized

    def _walk(value: object) -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                assert key not in {"created_at", "duration", "timestamp"}
                _walk(inner)
        elif isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(payload)
