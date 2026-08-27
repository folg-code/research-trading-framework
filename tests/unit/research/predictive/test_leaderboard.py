"""Single-study Predictive Research leaderboard ranking (D-S042-13)."""

from __future__ import annotations

import pytest

from trading_framework.research.predictive import (
    LeaderboardRowKind,
    LeaderboardRunSnapshot,
    PredictiveLeaderboard,
    PredictiveSpecError,
    TaskType,
    build_predictive_leaderboard,
    primary_metric_for_task,
)


def _snapshot(
    *,
    run_id: str,
    family: str,
    model_score: float | None,
    fingerprint: str = "dataset-fp",
    task_type: TaskType = TaskType.REGRESSION,
    constant: float | None = 0.05,
    permutation: float | None = 0.0,
) -> LeaderboardRunSnapshot:
    pooled: dict[str, float | None] = {"MODEL": model_score}
    if constant is not None:
        pooled["CONSTANT_MEAN"] = constant
    if permutation is not None:
        pooled["RANDOM_PERMUTATION"] = permutation
    return LeaderboardRunSnapshot(
        run_id=run_id,
        dataset_fingerprint=fingerprint,
        task_type=task_type,
        family=family,
        library="testlib",
        library_version="0.0",
        pooled_primary_by_source=pooled,
    )


def test_primary_metric_matches_task_type() -> None:
    assert primary_metric_for_task(TaskType.REGRESSION).value == "spearman_ic"
    assert primary_metric_for_task(TaskType.CLASSIFICATION).value == "roc_auc"


def test_leaderboard_ranks_higher_pooled_primary_first() -> None:
    board = build_predictive_leaderboard(
        (
            _snapshot(run_id="ridge", family="sklearn.ridge", model_score=0.20),
            _snapshot(run_id="xgb", family="xgboost.regressor", model_score=0.80),
        )
    )
    estimator_rows = [row for row in board.rows if row.kind is LeaderboardRowKind.ESTIMATOR]
    assert [row.family for row in estimator_rows] == ["xgboost.regressor", "sklearn.ridge"]
    assert estimator_rows[0].rank < estimator_rows[1].rank
    assert board.dataset_fingerprint == "dataset-fp"
    assert board.metric == "spearman_ic"
    baseline_sources = {row.source for row in board.rows if row.kind is LeaderboardRowKind.BASELINE}
    assert "CONSTANT_MEAN" in baseline_sources
    assert "RANDOM_PERMUTATION" in baseline_sources


def test_leaderboard_ranks_neural_families_beside_trees_and_baselines() -> None:
    board = build_predictive_leaderboard(
        (
            _snapshot(run_id="ridge", family="sklearn.ridge", model_score=0.20),
            _snapshot(run_id="xgb", family="xgboost.regressor", model_score=0.80),
            _snapshot(
                run_id="ff",
                family="torch.feedforward.regressor",
                model_score=0.45,
            ),
            _snapshot(run_id="lstm", family="torch.lstm.regressor", model_score=0.55),
        )
    )
    estimator_rows = [row for row in board.rows if row.kind is LeaderboardRowKind.ESTIMATOR]
    assert [row.family for row in estimator_rows] == [
        "xgboost.regressor",
        "torch.lstm.regressor",
        "torch.feedforward.regressor",
        "sklearn.ridge",
    ]
    baseline_sources = {row.source for row in board.rows if row.kind is LeaderboardRowKind.BASELINE}
    assert "CONSTANT_MEAN" in baseline_sources
    assert "RANDOM_PERMUTATION" in baseline_sources


def test_leaderboard_tie_keeps_first_declared_run() -> None:
    board = build_predictive_leaderboard(
        (
            _snapshot(
                run_id="first",
                family="sklearn.ridge",
                model_score=0.50,
                constant=None,
                permutation=None,
            ),
            _snapshot(
                run_id="second",
                family="sklearn.elastic_net",
                model_score=0.50,
                constant=None,
                permutation=None,
            ),
        )
    )
    assert [row.run_id for row in board.rows] == ["first", "second"]


def test_leaderboard_none_scores_rank_last() -> None:
    board = build_predictive_leaderboard(
        (
            _snapshot(
                run_id="missing",
                family="sklearn.ridge",
                model_score=None,
                constant=None,
                permutation=None,
            ),
            _snapshot(
                run_id="scored",
                family="xgboost.regressor",
                model_score=0.10,
                constant=None,
                permutation=None,
            ),
        )
    )
    assert [row.run_id for row in board.rows] == ["scored", "missing"]


def test_leaderboard_rejects_mismatched_fingerprints() -> None:
    with pytest.raises(PredictiveSpecError, match="dataset fingerprint"):
        build_predictive_leaderboard(
            (
                _snapshot(run_id="a", family="sklearn.ridge", model_score=0.1, fingerprint="fp-a"),
                _snapshot(run_id="b", family="sklearn.ridge", model_score=0.2, fingerprint="fp-b"),
            )
        )


def test_leaderboard_rejects_mismatched_task_types() -> None:
    with pytest.raises(PredictiveSpecError, match="task_type"):
        build_predictive_leaderboard(
            (
                _snapshot(run_id="a", family="sklearn.ridge", model_score=0.1),
                _snapshot(
                    run_id="b",
                    family="sklearn.logistic",
                    model_score=0.1,
                    task_type=TaskType.CLASSIFICATION,
                ),
            )
        )


def test_leaderboard_rejects_empty_and_missing_model_source() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one run"):
        build_predictive_leaderboard(())
    with pytest.raises(PredictiveSpecError, match="pooled MODEL"):
        build_predictive_leaderboard(
            (
                LeaderboardRunSnapshot(
                    run_id="empty",
                    dataset_fingerprint="fp",
                    task_type=TaskType.REGRESSION,
                    family="sklearn.ridge",
                    library="testlib",
                    library_version="0.0",
                    pooled_primary_by_source={"CONSTANT_MEAN": 0.0},
                ),
            )
        )


def test_leaderboard_from_dict_roundtrip() -> None:
    board = build_predictive_leaderboard(
        (_snapshot(run_id="ridge", family="sklearn.ridge", model_score=0.20),)
    )
    restored = PredictiveLeaderboard.from_dict(board.to_dict())
    assert restored.dataset_fingerprint == board.dataset_fingerprint
    assert restored.metric == board.metric
    assert [row.family for row in restored.rows] == [row.family for row in board.rows]
    assert restored.rows[0].kind is board.rows[0].kind
