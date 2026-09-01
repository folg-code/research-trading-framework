"""Tests for `trading-cli research run` (S046-T006 predictive, S046-T007 strategy).

Tier 1, network-free.

``research run strategy`` never touches an ML extra, so it is exercised
end-to-end against a real published dataset (same fixture/pattern as
tests/unit/scripts/test_run_strategy_research_cli.py).

``research run predictive`` composes three application calls that (through
``run_predictive_research``) resolve an estimator family, which requires the
optional ``ml``/``dl`` extras this workspace member must never depend on
(D-S046-11: "No ML extra in the CLI environment"). Those calls are faked here
-- the CLI's own coverage is the seam (config -> typed request -> typed
result flow), not the estimator fit itself, which already has its own
coverage under tests/unit/application/predictive_research/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from unittest.mock import patch

import pytest
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState
from trading_framework.time.models.timeframe import Timeframe

from trading_cli.cli import main
from trading_cli.commands import research as research_cmd
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS


def _write_config(tmp_path: Path, *, storage_root: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text.format(storage_root=storage_root.as_posix()), encoding="utf-8")
    return path


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> str:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="cli-research-run-strategy",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return str(result.dataset_ref)


def test_research_run_strategy_end_to_end(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            f"    dataset_ref: '{dataset_ref}'\n"
            "    timeframe: 1m\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["run_id"]
    assert result["strategy_model_id"] == "high_vol_higher_low_fixed_exit"


_FIXTURE_STRATEGY = (
    Path(__file__).parent / "fixtures" / "strategies" / "valid_strategy.py"
).resolve()


def test_research_run_strategy_file_dry_run_prints_loaded_id_and_path(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """S047-T003 / ADR-0027 Sec4: `--dry-run` proves the file loads pre-flight."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            f"    dataset_ref: '{dataset_ref}'\n"
            "    timeframe: 1m\n"
            f"    strategy_file: {_FIXTURE_STRATEGY.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    arguments = payload["plan"]["arguments"]
    assert arguments["strategy_model_id"] == "fixture_valid_strategy"
    assert arguments["strategy_file"] == str(_FIXTURE_STRATEGY)
    assert arguments["strategy_source"] == "strategy_file"


def test_research_run_strategy_file_end_to_end_uses_loaded_strategy(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PRD success metric 1: the run manifest carries the loaded strategy's id."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            f"    dataset_ref: '{dataset_ref}'\n"
            "    timeframe: 1m\n"
            f"    strategy_file: {_FIXTURE_STRATEGY.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["run_id"]
    assert result["strategy_model_id"] == "fixture_valid_strategy"


def test_research_run_strategy_without_strategy_file_still_uses_canonical(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-S047-05: an absent `strategy_file` resolves exactly as it did on main."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            f"    dataset_ref: '{dataset_ref}'\n"
            "    timeframe: 1m\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    arguments = payload["plan"]["arguments"]
    assert arguments["strategy_model_id"] == "high_vol_higher_low_fixed_exit"
    assert arguments["strategy_source"] == "canonical"
    assert "strategy_file" not in arguments


def test_research_run_strategy_file_missing_is_config_error(
    tmp_path: Path, ohlcv_sample_1m_path: Path
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    missing = tmp_path / "does_not_exist.py"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            f"    dataset_ref: '{dataset_ref}'\n"
            f"    strategy_file: {missing.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run"])

    assert exit_code == EXIT_CONFIG_ERROR


def test_research_run_strategy_missing_dataset_ref_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=("version: 1\nstorage_root: {storage_root}\n\nresearch:\n  kind: strategy\n"),
    )

    exit_code = main(["research", "run", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


@dataclass(frozen=True, slots=True)
class _FakeBuildResult:
    dataset_id: str


@dataclass(frozen=True, slots=True)
class _FakeRunResult:
    run_id: str
    persisted: bool


@dataclass(frozen=True, slots=True)
class _FakeRenderResult:
    run_id: str
    output_path: Path


def _write_definition(path: Path) -> None:
    payload = {
        "study_id": "cli_research_run_predictive_test",
        "dataset_ref": {
            "dataset_id": "ES.c.0|ohlcv|1m|csv|cli-research-run-predictive",
            "version": 1,
        },
        "time_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
        "evaluation_timeframe": "1m",
        "features": [
            {
                "component_id": "volatility.atr",
                "parameters": {"period": 2},
                "output_id": "value",
                "alias": "atr",
                "transform": "NONE",
            }
        ],
        "label": {"kind": "REGRESSION", "horizon": "5m"},
        "split": {
            "mode": "EXPANDING",
            "fold_count": 2,
            "test_span": "3h",
            "embargo_span": "15m",
            "min_train_rows": 10,
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_estimator(path: Path) -> None:
    payload = {
        "family": "sklearn.ridge",
        "hyperparameters": {"alpha": 1.0},
        "seed": 7,
        "task_type": "REGRESSION",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_research_run_predictive_composes_build_run_render(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    definition_path = tmp_path / "study.json"
    estimator_path = tmp_path / "estimator.json"
    _write_definition(definition_path)
    _write_estimator(estimator_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: predictive\n"
            "  predictive:\n"
            f"    definition: {definition_path.as_posix()}\n"
            f"    estimator: {estimator_path.as_posix()}\n"
        ),
    )
    calls: dict[str, object] = {}

    def fake_build(request: object) -> _FakeBuildResult:
        calls["build_storage_root"] = request.storage_root  # type: ignore[attr-defined]
        return _FakeBuildResult(dataset_id="dataset-abc")

    def fake_run(request: object) -> _FakeRunResult:
        calls["run_dataset_id"] = request.dataset_ref.dataset_id  # type: ignore[attr-defined]
        return _FakeRunResult(run_id="run-xyz", persisted=True)

    def fake_render(request: object) -> _FakeRenderResult:
        calls["render_run_id"] = request.run_ref.run_id  # type: ignore[attr-defined]
        return _FakeRenderResult(run_id="run-xyz", output_path=Path("report.html"))

    with (
        patch.object(research_cmd, "build_predictive_dataset", fake_build),
        patch.object(research_cmd, "run_predictive_research", fake_run),
        patch.object(research_cmd, "render_predictive_research_report", fake_render),
    ):
        exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    # the dataset_id produced by "build" flows into "run" as a typed value,
    # never round-tripped through stdout (SPRINT_046.md §4 finding 1)
    assert calls["run_dataset_id"] == "dataset-abc"
    assert calls["render_run_id"] == "run-xyz"
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["dataset_id"] == "dataset-abc"
    assert payload["result"]["run_id"] == "run-xyz"
    assert payload["result"]["output_path"] == "report.html"


def test_research_run_predictive_skips_render_when_disabled(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    definition_path = tmp_path / "study.json"
    estimator_path = tmp_path / "estimator.json"
    _write_definition(definition_path)
    _write_estimator(estimator_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: predictive\n"
            "  predictive:\n"
            f"    definition: {definition_path.as_posix()}\n"
            f"    estimator: {estimator_path.as_posix()}\n"
            "    render_report: false\n"
        ),
    )
    render_called = False

    def fake_build(request: object) -> _FakeBuildResult:
        return _FakeBuildResult(dataset_id="dataset-abc")

    def fake_run(request: object) -> _FakeRunResult:
        return _FakeRunResult(run_id="run-xyz", persisted=True)

    def fake_render(request: object) -> _FakeRenderResult:
        nonlocal render_called
        render_called = True
        return _FakeRenderResult(run_id="run-xyz", output_path=Path("report.html"))

    with (
        patch.object(research_cmd, "build_predictive_dataset", fake_build),
        patch.object(research_cmd, "run_predictive_research", fake_run),
        patch.object(research_cmd, "render_predictive_research_report", fake_render),
    ):
        exit_code = main(["research", "run", "--config", str(config_path)])

    assert exit_code == EXIT_SUCCESS
    assert render_called is False


def test_research_run_predictive_missing_definition_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    estimator_path = tmp_path / "estimator.json"
    _write_estimator(estimator_path)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: predictive\n"
            "  predictive:\n"
            f"    estimator: {estimator_path.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR
