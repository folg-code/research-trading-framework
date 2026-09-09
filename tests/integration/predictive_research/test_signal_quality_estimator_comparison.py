"""Estimator comparison + threshold sensitivity worked example (Sprint 058 T002).

T001 proved the SIGNAL_QUALITY + signal_occurrences plumbing end to end, on a
deliberately minimal fixture (14 rows, one fold) whose job was proving the
pipeline is task-agnostic, not comparing model quality. This test reuses the
shared synthetic-signal fixture (`_fixtures.py`, already the Sprint 042/043
precedent for estimator comparison across `run_predictive_research` calls)
because a real comparison needs enough row/feature variance to be meaningful
-- the same underlying question T001's study asks (does a model separate
higher- from lower-quality outcomes?), just on data shaped to answer it.

Two leaderboards, by construction of `build_predictive_leaderboard` requiring
one shared `task_type` per leaderboard (`PredictiveSpecError` otherwise):

- REGRESSION: sklearn.ridge vs sklearn.elastic_net -- both promotable
  (Q6 = Option B), a genuine promotable-family comparison on a continuous
  quality label.
- CLASSIFICATION: sklearn.logistic (promotable) vs xgboost.classifier
  (research-only) on the same dataset fingerprint -- one leaderboard can
  legitimately contain both (`leaderboard.py` ranks by pooled metric with no
  allow-list awareness), so "clearly separated" is enforced by this test's
  own partition against the canonical `MODEL_FAMILY_ALLOWLIST`, never by
  silently treating every ranked row as gate-eligible.

Each pair of families is fit against ONE shared, once-written dataset (not
one dataset per family, which `run_fixture()` alone cannot do -- it always
writes a fresh dataset and refuses to overwrite one) -- this is what makes
the comparison a comparison: two estimators scored on the same rows, the
same folds, the same dataset fingerprint.

Threshold sensitivity (`analyze_threshold_sensitivity`) is computed for the
logistic run -- the promotable, gate-eligible classifier -- since a
probability threshold is what T003/T004's strategy gate will actually
declare.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.application.predictive_research import (
    AnalyzeThresholdSensitivityRequest,
    ComparePredictiveRunsRequest,
    RunPredictiveResearchRequest,
    analyze_threshold_sensitivity,
    compare_predictive_runs,
    run_predictive_research,
)
from trading_framework.application.predictive_research.run_predictive_research import (
    RunPredictiveResearchResult,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_dir
from trading_framework.research.datasets.predictive import PredictiveDatasetRef
from trading_framework.research.datasets.promoted_artifact import MODEL_FAMILY_ALLOWLIST
from trading_framework.research.predictive import (
    DEFAULT_THRESHOLD_GRID,
    EstimatorSpec,
    LeaderboardRowKind,
    PreprocessingSpec,
    PreprocessingStep,
    TaskType,
)
from trading_framework.time.clocks.fixed import FixedClock

from ._fixtures import estimator, labelled_rows, write_dataset

pytest.importorskip("sklearn")
pytest.importorskip("xgboost")

pytestmark = pytest.mark.ml_trees

#: xgboost's classifier/regressor factories reject sklearn's alpha/C
#: hyperparameter names (`_reject_unknown_hyperparameters`) -- `_fixtures.py`'s
#: `estimator()` only knows the two sklearn shapes, so the research-only tree
#: family used here for comparison needs its own small, valid hyperparameter
#: set, mirroring `test_predictive_tree_comparison.py`'s own fixture.
_TREE_HYPERPARAMETERS = {"n_estimators": 40, "max_depth": 3, "learning_rate": 0.1}


def _estimator_spec(family: str, task_type: TaskType) -> EstimatorSpec:
    if family.startswith("xgboost."):
        return EstimatorSpec(
            family=family, hyperparameters=_TREE_HYPERPARAMETERS, seed=7, task_type=task_type
        )
    return estimator(family, task_type)


def _fit(
    storage_root: Path,
    dataset_ref: PredictiveDatasetRef,
    *,
    family: str,
    task_type: TaskType,
) -> RunPredictiveResearchResult:
    return run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=_estimator_spec(family, task_type),
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )


def test_promotable_family_comparison_on_regression_label(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = write_dataset(
        storage_root,
        labelled_rows(mode="regression"),
        dataset_id="signal_quality_regression",
        label_kind="REGRESSION",
    )

    ridge_run = _fit(
        storage_root, dataset_ref, family="sklearn.ridge", task_type=TaskType.REGRESSION
    )
    elastic_net_run = _fit(
        storage_root,
        dataset_ref,
        family="sklearn.elastic_net",
        task_type=TaskType.REGRESSION,
    )

    result = compare_predictive_runs(
        ComparePredictiveRunsRequest(
            run_dirs=(
                predictive_research_run_dir(storage_root, ridge_run.run_id),
                predictive_research_run_dir(storage_root, elastic_net_run.run_id),
            )
        )
    )

    estimator_families = {
        row.family for row in result.leaderboard.rows if row.kind is LeaderboardRowKind.ESTIMATOR
    }
    assert estimator_families == {"sklearn.ridge", "sklearn.elastic_net"}
    assert estimator_families <= MODEL_FAMILY_ALLOWLIST
    assert result.output_path.exists()


def test_promotable_vs_research_only_comparison_on_binary_label_is_partitionable(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = write_dataset(
        storage_root,
        labelled_rows(mode="binary"),
        dataset_id="signal_quality_binary",
        label_kind="BINARY",
    )

    logistic_run = _fit(
        storage_root,
        dataset_ref,
        family="sklearn.logistic",
        task_type=TaskType.CLASSIFICATION,
    )
    tree_run = _fit(
        storage_root,
        dataset_ref,
        family="xgboost.classifier",
        task_type=TaskType.CLASSIFICATION,
    )

    result = compare_predictive_runs(
        ComparePredictiveRunsRequest(
            run_dirs=(
                predictive_research_run_dir(storage_root, logistic_run.run_id),
                predictive_research_run_dir(storage_root, tree_run.run_id),
            )
        )
    )

    estimator_rows = {
        row.family: row
        for row in result.leaderboard.rows
        if row.kind is LeaderboardRowKind.ESTIMATOR
    }
    assert set(estimator_rows) == {"sklearn.logistic", "xgboost.classifier"}

    # Never treat every ranked row as gate-eligible -- the leaderboard itself
    # carries no allow-list awareness (leaderboard.py), so this partition is
    # the "clearly separated" requirement in code, not merely in a docstring.
    gate_eligible = {family for family in estimator_rows if family in MODEL_FAMILY_ALLOWLIST}
    research_only = {family for family in estimator_rows if family not in MODEL_FAMILY_ALLOWLIST}
    assert gate_eligible == {"sklearn.logistic"}
    assert research_only == {"xgboost.classifier"}

    # sklearn.logistic is the gate-eligible classifier -- threshold
    # sensitivity is meaningful for it, matching what T003/T004's strategy
    # gate will actually declare.
    sensitivity = analyze_threshold_sensitivity(
        AnalyzeThresholdSensitivityRequest(run_ref=logistic_run.run_ref, storage_root=storage_root)
    )
    assert len(sensitivity.report.points) == len(DEFAULT_THRESHOLD_GRID)
    assert sensitivity.output_path is not None
    assert sensitivity.output_path.exists()


def test_family_allowlist_is_unchanged_by_this_sprint() -> None:
    """SPRINT_058.md's out-of-scope constraint, asserted, not just declared."""
    assert frozenset({"sklearn.ridge", "sklearn.elastic_net", "sklearn.logistic"}) == (
        MODEL_FAMILY_ALLOWLIST
    )
    assert estimator("sklearn.ridge", TaskType.REGRESSION).family in MODEL_FAMILY_ALLOWLIST
