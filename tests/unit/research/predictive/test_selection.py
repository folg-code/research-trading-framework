"""Bounded candidate-set validation, inner split, and early-stopping guards."""

from __future__ import annotations

import pytest

from trading_framework.research.predictive import (
    CandidateSetSpec,
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    SelectionMetric,
    SelectionTrace,
    TaskType,
    candidate_identity_hash,
    require_early_stopping_eval_roles,
    select_winning_index,
    split_inner_train_validation,
)
from trading_framework.research.predictive.selection import (
    CandidateFoldScore,
    FoldSelectionTrace,
)


def _ridge(*, alpha: float, seed: int = 7) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": alpha},
        seed=seed,
        task_type=TaskType.REGRESSION,
    )


def _logistic(*, c_value: float) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.logistic",
        hyperparameters={"C": c_value},
        seed=3,
        task_type=TaskType.CLASSIFICATION,
    )


def test_candidate_set_accepts_declared_cap() -> None:
    spec = CandidateSetSpec(
        candidates=(_ridge(alpha=0.5), _ridge(alpha=1.0)),
        max_candidates=8,
        selection_metric=SelectionMetric.SPEARMAN_IC,
    )
    assert spec.task_type is TaskType.REGRESSION
    assert spec.to_dict()["max_candidates"] == 8
    restored = CandidateSetSpec.from_dict(spec.to_dict())
    assert restored.candidates[1].hyperparameters["alpha"] == 1.0


def test_candidate_set_rejects_over_cap() -> None:
    with pytest.raises(PredictiveSpecError, match="max_candidates is 1"):
        CandidateSetSpec(
            candidates=(_ridge(alpha=0.5), _ridge(alpha=1.0)),
            max_candidates=1,
        )


def test_candidate_set_rejects_cap_above_hard_limit() -> None:
    with pytest.raises(PredictiveSpecError, match="must be <= 16"):
        CandidateSetSpec(candidates=(_ridge(alpha=1.0),), max_candidates=17)


def test_candidate_set_rejects_empty() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one candidate"):
        CandidateSetSpec(candidates=())


def test_candidate_set_rejects_mixed_task_types() -> None:
    with pytest.raises(PredictiveSpecError, match="same task_type"):
        CandidateSetSpec(candidates=(_ridge(alpha=1.0), _logistic(c_value=1.0)))


def test_candidate_set_rejects_metric_task_mismatch() -> None:
    with pytest.raises(PredictiveSpecError, match="does not match"):
        CandidateSetSpec(
            candidates=(_ridge(alpha=1.0),),
            selection_metric=SelectionMetric.ROC_AUC,
        )


def test_candidate_set_rejects_duplicate_identity() -> None:
    with pytest.raises(PredictiveSpecError, match="duplicate"):
        CandidateSetSpec(candidates=(_ridge(alpha=1.0), _ridge(alpha=1.0)))


def test_candidate_set_rejects_fraction_out_of_range() -> None:
    with pytest.raises(PredictiveSpecError, match="inner_validation_fraction"):
        CandidateSetSpec(
            candidates=(_ridge(alpha=1.0),),
            inner_validation_fraction=0.6,
        )


def test_classification_metric_defaults_to_roc_auc() -> None:
    spec = CandidateSetSpec(
        candidates=(_logistic(c_value=0.5), _logistic(c_value=1.0)),
        selection_metric=SelectionMetric.ROC_AUC,
    )
    assert spec.selection_metric is SelectionMetric.ROC_AUC


def test_inner_split_uses_chronological_suffix() -> None:
    inner_train, inner_val = split_inner_train_validation(50, inner_validation_fraction=0.2)
    assert list(inner_train) == list(range(40))
    assert list(inner_val) == list(range(40, 50))


def test_inner_split_rejects_too_few_rows() -> None:
    with pytest.raises(PredictiveSpecError, match="at least 10"):
        split_inner_train_validation(20, inner_validation_fraction=0.2)


def test_select_winning_index_is_stable_on_ties() -> None:
    assert select_winning_index((0.1, 0.4, 0.4, 0.2)) == 1


def test_select_winning_index_skips_null_scores() -> None:
    assert select_winning_index((None, 0.2, None)) == 1


def test_select_winning_index_rejects_all_null() -> None:
    with pytest.raises(PredictiveSpecError, match="scored null"):
        select_winning_index((None, None))


def test_early_stopping_rejects_outer_test_roles() -> None:
    with pytest.raises(PredictiveSpecError, match="cannot reference outer TEST"):
        require_early_stopping_eval_roles((FoldRole.TRAIN, FoldRole.TEST))


def test_early_stopping_rejects_purged_and_embargoed() -> None:
    with pytest.raises(PredictiveSpecError, match="leak-guard"):
        require_early_stopping_eval_roles((FoldRole.PURGED,))
    with pytest.raises(PredictiveSpecError, match="leak-guard"):
        require_early_stopping_eval_roles((FoldRole.EMBARGOED,))


def test_early_stopping_accepts_train_only() -> None:
    require_early_stopping_eval_roles((FoldRole.TRAIN, FoldRole.TRAIN))


def test_selection_trace_from_dict_roundtrip() -> None:
    spec = _ridge(alpha=1.0)
    trace = SelectionTrace(
        selection_metric=SelectionMetric.SPEARMAN_IC,
        inner_validation_fraction=0.2,
        folds=(
            FoldSelectionTrace(
                fold_id=0,
                winner=spec,
                candidates=(
                    CandidateFoldScore(
                        family=spec.family,
                        hyperparameters=spec.hyperparameters,
                        seed=spec.seed,
                        identity_hash="ridge",
                        inner_validation_score=0.2,
                        selected=True,
                    ),
                ),
            ),
        ),
    )
    restored = SelectionTrace.from_dict(trace.to_dict())
    assert restored.selection_metric is SelectionMetric.SPEARMAN_IC
    assert restored.folds[0].winner.family == spec.family
    assert restored.folds[0].candidates[0].inner_validation_score == pytest.approx(0.2)


def test_candidate_identity_hash_is_stable() -> None:
    first = candidate_identity_hash(_ridge(alpha=1.0))
    second = candidate_identity_hash(_ridge(alpha=1.0))
    other = candidate_identity_hash(_ridge(alpha=2.0))
    assert first == second
    assert first != other
