"""Extra-free tests for Predictive Research study leaderboard orchestration."""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

import pytest

from trading_framework.application.predictive_research import (
    ComparePredictiveRunsRequest,
    compare_predictive_runs,
)
from trading_framework.research.predictive import LeaderboardRowKind, PredictiveSpecError

_COMPARE_IMPL = importlib.import_module(
    "trading_framework.application.predictive_research.compare_predictive_runs"
)


def _write_run(
    run_dir: Path,
    *,
    run_id: str,
    family: str,
    fingerprint: str,
    model_score: float,
    constant: float = 0.05,
    permutation: float = 0.0,
    task_type: str = "REGRESSION",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "dataset_fingerprint": fingerprint,
                "estimator_spec": {
                    "family": family,
                    "hyperparameters": {"alpha": 1.0},
                    "seed": 7,
                    "task_type": task_type,
                },
                "library": "testlib",
                "library_version": "0.0",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "pooled": {
                    "MODEL": {"statistical": {"spearman_ic": model_score, "roc_auc": None}},
                    "CONSTANT_MEAN": {"statistical": {"spearman_ic": constant, "roc_auc": None}},
                    "RANDOM_PERMUTATION": {
                        "statistical": {"spearman_ic": permutation, "roc_auc": None}
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def test_compare_writes_leaderboard_next_to_first_run(tmp_path: Path) -> None:
    first = tmp_path / "runs" / "ridge"
    second = tmp_path / "runs" / "xgb"
    _write_run(first, run_id="ridge", family="sklearn.ridge", fingerprint="fp-1", model_score=0.2)
    _write_run(
        second, run_id="xgb", family="xgboost.regressor", fingerprint="fp-1", model_score=0.9
    )

    result = compare_predictive_runs(ComparePredictiveRunsRequest(run_dirs=(first, second)))

    output = first / "leaderboard.json"
    assert result.output_path == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    estimator_rows = [row for row in payload["rows"] if row["kind"] == LeaderboardRowKind.ESTIMATOR]
    assert [row["family"] for row in estimator_rows] == ["xgboost.regressor", "sklearn.ridge"]
    assert payload["dataset_fingerprint"] == "fp-1"


def test_compare_ranks_neural_families_beside_trees_and_baselines(tmp_path: Path) -> None:
    ridge = tmp_path / "ridge"
    xgb = tmp_path / "xgb"
    feedforward = tmp_path / "ff"
    lstm = tmp_path / "lstm"
    _write_run(ridge, run_id="ridge", family="sklearn.ridge", fingerprint="fp-n", model_score=0.20)
    _write_run(xgb, run_id="xgb", family="xgboost.regressor", fingerprint="fp-n", model_score=0.80)
    _write_run(
        feedforward,
        run_id="ff",
        family="torch.feedforward.regressor",
        fingerprint="fp-n",
        model_score=0.45,
    )
    _write_run(
        lstm, run_id="lstm", family="torch.lstm.regressor", fingerprint="fp-n", model_score=0.55
    )

    result = compare_predictive_runs(
        ComparePredictiveRunsRequest(run_dirs=(ridge, xgb, feedforward, lstm))
    )

    estimator_rows = [
        row for row in result.leaderboard.rows if row.kind is LeaderboardRowKind.ESTIMATOR
    ]
    assert [row.family for row in estimator_rows] == [
        "xgboost.regressor",
        "torch.lstm.regressor",
        "torch.feedforward.regressor",
        "sklearn.ridge",
    ]
    baseline_sources = {
        row.source for row in result.leaderboard.rows if row.kind is LeaderboardRowKind.BASELINE
    }
    assert "CONSTANT_MEAN" in baseline_sources
    assert "RANDOM_PERMUTATION" in baseline_sources


def test_compare_honors_caller_output_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run(run_dir, run_id="ridge", family="sklearn.ridge", fingerprint="fp-1", model_score=0.3)
    destination = tmp_path / "out" / "board.json"
    result = compare_predictive_runs(
        ComparePredictiveRunsRequest(run_dirs=(run_dir,), output_path=destination)
    )
    assert result.output_path == destination
    assert destination.exists()


def test_compare_rejects_mismatched_fingerprints(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    _write_run(first, run_id="a", family="sklearn.ridge", fingerprint="fp-a", model_score=0.1)
    _write_run(second, run_id="b", family="sklearn.ridge", fingerprint="fp-b", model_score=0.2)
    with pytest.raises(PredictiveSpecError, match="dataset fingerprint"):
        compare_predictive_runs(ComparePredictiveRunsRequest(run_dirs=(first, second)))


def test_compare_rejects_missing_metrics(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "ridge",
                "dataset_fingerprint": "fp",
                "estimator_spec": {
                    "family": "sklearn.ridge",
                    "hyperparameters": {},
                    "seed": 1,
                    "task_type": "REGRESSION",
                },
                "library": "testlib",
                "library_version": "0.0",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PredictiveSpecError, match=r"metrics\.json"):
        compare_predictive_runs(ComparePredictiveRunsRequest(run_dirs=(run_dir,)))


def test_compare_module_does_not_import_ml_libraries() -> None:
    assert _COMPARE_IMPL.__file__ is not None
    imported: list[str] = []
    tree = ast.parse(Path(_COMPARE_IMPL.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in ("sklearn", "xgboost", "lightgbm", "catboost", "torch")
    )
    assert "trading_framework.infrastructure.ml" not in imported
