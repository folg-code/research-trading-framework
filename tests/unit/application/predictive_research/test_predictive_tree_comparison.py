"""T020: tree families vs S040 baselines on the known-signal fixture (D-S042-15).

Synthetic labelled frames only — no NQ. Each tree family must beat
RANDOM_PERMUTATION on the same folds as ridge. Noise labels must stay inside
the permutation-baseline spread (boosting must not invent structure).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit.application.predictive_research.test_predictive_known_signal import (
    _NOISE_SPEARMAN_BAND,
    _SIGNAL_RANK_IC_FLOOR,
    _SIGNAL_VS_PERMUTATION_MARGIN,
    _assert_within_permutation_spread,
    _labelled_rows,
    _statistical,
    _write_dataset,
)
from trading_framework.application.predictive_research import (
    ComparePredictiveRunsRequest,
    RunPredictiveResearchRequest,
    compare_predictive_runs,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_dir
from trading_framework.research.datasets.predictive import PredictiveDatasetRef
from trading_framework.research.predictive import (
    EstimatorSpec,
    LeaderboardRowKind,
    MetricSource,
    PredictiveMetricsReport,
    TaskType,
)
from trading_framework.time.clocks.fixed import FixedClock

pytest.importorskip("xgboost")
pytest.importorskip("lightgbm")
pytest.importorskip("catboost")
pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml_trees

_TREE_REGRESSORS = (
    "xgboost.regressor",
    "lightgbm.regressor",
    "catboost.regressor",
)
_COMPARISON_FAMILIES = ("sklearn.ridge", *_TREE_REGRESSORS)


def _spec(family: str) -> EstimatorSpec:
    if family == "sklearn.ridge":
        hyperparameters: dict[str, object] = {"alpha": 0.1}
    else:
        hyperparameters = {"n_estimators": 40, "max_depth": 3, "learning_rate": 0.1}
    return EstimatorSpec(
        family=family,
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _run(
    storage_root: Path,
    dataset_ref: PredictiveDatasetRef,
    spec: EstimatorSpec,
) -> tuple[str, PredictiveMetricsReport]:
    result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=spec,
            storage_root=storage_root,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )
    return result.run_id, result.metrics


def test_tree_families_recover_known_signal_and_share_a_leaderboard(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="known_signal"),
        dataset_id="treeknownsignal01",
        label_kind="REGRESSION",
    )
    run_ids: list[str] = []
    for family in _COMPARISON_FAMILIES:
        run_id, report = _run(storage_root, dataset_ref, _spec(family))
        run_ids.append(run_id)
        model_ic = _statistical(report, MetricSource.MODEL.value, "spearman_ic", missing=0.0)
        perm_ic = _statistical(
            report, MetricSource.RANDOM_PERMUTATION.value, "spearman_ic", missing=0.0
        )
        assert model_ic > _SIGNAL_RANK_IC_FLOOR, family
        assert model_ic > perm_ic + _SIGNAL_VS_PERMUTATION_MARGIN, family

    board = compare_predictive_runs(
        ComparePredictiveRunsRequest(
            run_dirs=tuple(predictive_research_run_dir(storage_root, run_id) for run_id in run_ids)
        )
    )
    estimator_families = {
        row.family for row in board.leaderboard.rows if row.kind is LeaderboardRowKind.ESTIMATOR
    }
    baseline_sources = {
        row.source for row in board.leaderboard.rows if row.kind is LeaderboardRowKind.BASELINE
    }
    assert estimator_families == set(_COMPARISON_FAMILIES)
    assert MetricSource.CONSTANT_MEAN.value in baseline_sources
    assert MetricSource.RANDOM_PERMUTATION.value in baseline_sources
    assert board.leaderboard.dataset_fingerprint == "treeknownsignal01" + ("d" * 48)
    assert board.output_path.exists()


def test_tree_families_on_noise_labels_stay_within_permutation_spread(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(
        storage_root,
        _labelled_rows(mode="noise"),
        dataset_id="treenoiselabel01",
        label_kind="REGRESSION",
    )
    for family in _TREE_REGRESSORS:
        _run_id, report = _run(storage_root, dataset_ref, _spec(family))
        _assert_within_permutation_spread(
            report, "spearman_ic", band=_NOISE_SPEARMAN_BAND, missing=0.0
        )
