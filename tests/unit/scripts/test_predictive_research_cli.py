"""CLI tests for Predictive Research run and analyze scripts."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from scripts.predictive_research import analyze_predictive_run as analyze_cli
from scripts.predictive_research import compare_predictive_runs as compare_cli
from scripts.predictive_research import promote_predictive_run as promote_cli
from scripts.predictive_research import render_predictive_report as render_cli
from scripts.predictive_research import run_predictive_research as run_cli

from trading_framework.application.predictive_research import (
    AnalyzePredictiveRunRequest,
    PromotePredictiveRunRequest,
    RenderPredictiveReportRequest,
    RunPredictiveResearchRequest,
)
from trading_framework.research.predictive.estimators import EstimatorSpec, TaskType

_ML_LIBRARY_ROOTS = ("sklearn", "xgboost", "lightgbm", "catboost", "torch")


@dataclass(frozen=True, slots=True)
class _FakeRunResult:
    run_id: str
    fingerprint: str
    persisted: bool


@dataclass(frozen=True, slots=True)
class _FakeRenderResult:
    run_id: str
    output_path: Path


@dataclass(frozen=True, slots=True)
class _FakeAnalyzeResult:
    run_id: str
    report: Any
    metrics_path: Path | None


@dataclass(frozen=True, slots=True)
class _FakePromoteResult:
    artifact_fingerprint: str
    directory: Path
    fold_id: int


class _FakeMetricsReport:
    def __init__(self, *, folds: dict[str, Any], pooled: dict[str, Any]) -> None:
        self._folds = folds
        self._pooled = pooled

    def to_dict(self) -> dict[str, Any]:
        return {"folds": self._folds, "pooled": self._pooled}


def _flag_args(storage_root: Path, *, extra: list[str] | None = None) -> list[str]:
    args = [
        "--storage-root",
        str(storage_root),
        "--dataset-id",
        "dataset-cli",
        "--family",
        "sklearn.ridge",
        "--seed",
        "7",
        "--task-type",
        "REGRESSION",
    ]
    if extra:
        args.extend(extra)
    return args


def _imported_modules(source: str) -> list[str]:
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    return imported


def test_run_cli_missing_estimator_spec_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli.main(["--storage-root", str(tmp_path), "--dataset-id", "dataset-cli"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "provide --estimator or --family, --seed, and --task-type" in captured.err


def test_run_cli_missing_estimator_file_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli.main(
        [
            "--storage-root",
            str(tmp_path),
            "--dataset-id",
            "dataset-cli",
            "--estimator",
            str(tmp_path / "missing.json"),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "estimator file not found" in captured.err


def test_run_cli_rejects_mixed_spec_sources(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec_path = tmp_path / "estimator.json"
    spec_path.write_text(
        json.dumps(
            {
                "family": "sklearn.ridge",
                "hyperparameters": {},
                "seed": 7,
                "task_type": "REGRESSION",
            }
        ),
        encoding="utf-8",
    )
    exit_code = run_cli.main(
        [
            "--storage-root",
            str(tmp_path),
            "--dataset-id",
            "dataset-cli",
            "--estimator",
            str(spec_path),
            "--family",
            "sklearn.ridge",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not both" in captured.err


def test_run_cli_from_flags_prints_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_request: dict[str, Any] = {}

    def fake_run(request: RunPredictiveResearchRequest) -> _FakeRunResult:
        captured_request["request"] = request
        return _FakeRunResult(run_id="run-cli", fingerprint="fp-cli", persisted=True)

    monkeypatch.setattr(run_cli, "run_predictive_research", fake_run)
    exit_code = run_cli.main(
        _flag_args(
            tmp_path,
            extra=["--hyperparameters", '{"alpha": 1.0}', "--json"],
        )
    )
    payload = json.loads(capsys.readouterr().out)
    request = captured_request["request"]
    assert exit_code == 0
    assert payload == {"run_id": "run-cli", "fingerprint": "fp-cli", "persisted": True}
    assert request.dataset_ref.dataset_id == "dataset-cli"
    assert request.persist is True
    assert request.estimator == EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def test_run_cli_from_yaml_and_no_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec_path = tmp_path / "estimator.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "family: sklearn.logistic",
                "hyperparameters:",
                "  C: 0.5",
                "seed: 3",
                "task_type: CLASSIFICATION",
            ]
        ),
        encoding="utf-8",
    )
    captured_request: dict[str, Any] = {}

    def fake_run(request: RunPredictiveResearchRequest) -> _FakeRunResult:
        captured_request["request"] = request
        return _FakeRunResult(run_id="run-yaml", fingerprint="fp-yaml", persisted=False)

    monkeypatch.setattr(run_cli, "run_predictive_research", fake_run)
    exit_code = run_cli.main(
        [
            "--storage-root",
            str(tmp_path),
            "--dataset-id",
            "dataset-yaml",
            "--estimator",
            str(spec_path),
            "--no-persist",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    request = captured_request["request"]
    assert exit_code == 0
    assert payload["persisted"] is False
    assert request.persist is False
    assert request.estimator.family == "sklearn.logistic"
    assert request.estimator.task_type is TaskType.CLASSIFICATION
    assert request.estimator.seed == 3
    assert dict(request.estimator.hyperparameters) == {"C": 0.5}


def test_run_cli_invalid_hyperparameters_json_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli.main(_flag_args(tmp_path, extra=["--hyperparameters", "[1, 2]"]))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "hyperparameters must be a mapping" in captured.err


def test_run_cli_missing_dataset_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli.main(_flag_args(tmp_path))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing manifest" in captured.err


def test_analyze_cli_missing_run_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = analyze_cli.main(["--storage-root", str(tmp_path), "--run-id", "missing-run"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing manifest" in captured.err


def test_analyze_cli_prints_pooled_summary_and_fold_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metrics_path = tmp_path / "metrics.json"
    report = _FakeMetricsReport(
        folds={"0": {"MODEL": {}}, "1": {"MODEL": {}}},
        pooled={
            "MODEL": {"statistical": {"rmse": 0.1}},
            "CONSTANT_MEAN": {"statistical": {"rmse": 0.2}},
            "RANDOM_PERMUTATION": {"statistical": {"rmse": 0.3}},
        },
    )

    def fake_analyze(request: AnalyzePredictiveRunRequest) -> _FakeAnalyzeResult:
        assert request.run_ref.run_id == "run-analyze"
        assert request.persist is True
        return _FakeAnalyzeResult(
            run_id="run-analyze",
            report=report,
            metrics_path=metrics_path,
        )

    monkeypatch.setattr(analyze_cli, "analyze_predictive_run", fake_analyze)
    exit_code = analyze_cli.main(
        [
            "--storage-root",
            str(tmp_path),
            "--run-id",
            "run-analyze",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["run_id"] == "run-analyze"
    assert payload["fold_count"] == 2
    assert payload["fold_ids"] == ["0", "1"]
    assert payload["pooled_sources"] == ["MODEL", "CONSTANT_MEAN", "RANDOM_PERMUTATION"]
    assert payload["pooled"]["MODEL"]["statistical"]["rmse"] == 0.1
    assert payload["metrics_path"] == str(metrics_path)


def test_analyze_cli_text_summary_mentions_per_fold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _FakeMetricsReport(
        folds={"0": {"MODEL": {}}},
        pooled={"MODEL": {}},
    )

    def fake_analyze(request: AnalyzePredictiveRunRequest) -> _FakeAnalyzeResult:
        assert request.run_ref.run_id == "run-text"
        return _FakeAnalyzeResult(
            run_id="run-text",
            report=report,
            metrics_path=tmp_path / "m.json",
        )

    monkeypatch.setattr(analyze_cli, "analyze_predictive_run", fake_analyze)
    exit_code = analyze_cli.main(["--storage-root", str(tmp_path), "--run-id", "run-text"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "fold_count: 1" in output
    assert "per-fold" in output


def test_render_cli_missing_run_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = render_cli.main(["--storage-root", str(tmp_path), "--run-id", "missing-run"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing manifest" in captured.err


def test_render_cli_prints_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "report.html"

    def fake_render(request: RenderPredictiveReportRequest) -> _FakeRenderResult:
        assert request.run_ref.run_id == "run-html"
        assert request.storage_root == tmp_path
        assert request.output_path is None
        return _FakeRenderResult(run_id="run-html", output_path=output_path)

    monkeypatch.setattr(render_cli, "render_predictive_research_report", fake_render)
    exit_code = render_cli.main(["--storage-root", str(tmp_path), "--run-id", "run-html", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["run_id"] == "run-html"
    assert payload["output_path"] == str(output_path)


def test_promote_cli_missing_run_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = promote_cli.main(["--storage-root", str(tmp_path), "--run-id", "missing-run"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing manifest" in captured.err


def test_promote_cli_prints_fingerprint_and_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = tmp_path / "promoted" / ("f" * 64)

    def fake_promote(request: PromotePredictiveRunRequest) -> _FakePromoteResult:
        assert request.run_ref.run_id == "run-promote"
        assert request.storage_root == tmp_path
        return _FakePromoteResult(artifact_fingerprint="f" * 64, directory=directory, fold_id=1)

    monkeypatch.setattr(promote_cli, "promote_predictive_run", fake_promote)
    exit_code = promote_cli.main(
        ["--storage-root", str(tmp_path), "--run-id", "run-promote", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["artifact_fingerprint"] == "f" * 64
    assert payload["directory"] == str(directory)
    assert payload["fold_id"] == 1


def test_compare_cli_writes_leaderboard_and_prints_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "ridge"
    second = tmp_path / "xgb"
    first.mkdir()
    second.mkdir()
    for run_dir, run_id, family, score in (
        (first, "ridge", "sklearn.ridge", 0.2),
        (second, "xgb", "xgboost.regressor", 0.9),
    ):
        (run_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "dataset_fingerprint": "fp-1",
                    "estimator_spec": {
                        "family": family,
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
        (run_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "pooled": {
                        "MODEL": {"statistical": {"spearman_ic": score}},
                        "CONSTANT_MEAN": {"statistical": {"spearman_ic": 0.0}},
                        "RANDOM_PERMUTATION": {"statistical": {"spearman_ic": 0.0}},
                    }
                }
            ),
            encoding="utf-8",
        )
    exit_code = compare_cli.main(["--run-dir", str(first), "--run-dir", str(second), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["dataset_fingerprint"] == "fp-1"
    estimator_rows = [row for row in payload["rows"] if row["kind"] == "ESTIMATOR"]
    assert [row["family"] for row in estimator_rows] == ["xgboost.regressor", "sklearn.ridge"]
    assert (first / "leaderboard.json").exists()


def test_clis_are_thin_and_do_not_import_ml_libraries() -> None:
    for module in (run_cli, analyze_cli, render_cli, compare_cli, promote_cli):
        module_path = module.__file__
        assert module_path is not None
        imported = _imported_modules(Path(module_path).read_text(encoding="utf-8"))
        assert "trading_framework.application.predictive_research" in imported
        assert "trading_framework.infrastructure.ml" not in imported
        assert not any(name.startswith("trading_framework.infrastructure.ml.") for name in imported)
        assert not any(
            name == root or name.startswith(f"{root}.")
            for name in imported
            for root in _ML_LIBRARY_ROOTS
        )
