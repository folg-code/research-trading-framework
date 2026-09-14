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


def _strip_phase_event_lines(stdout: str) -> str:
    """Drop `research run signal`'s compact phase-event lines (T005), leaving
    the pretty-printed `--json` summary `dump_json` prints alongside them."""
    remaining_lines = []
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            remaining_lines.append(line)
            continue
        if isinstance(payload, dict) and payload.get("event") == "phase":
            continue
        remaining_lines.append(line)
    return "\n".join(remaining_lines)


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


@dataclass(frozen=True, slots=True)
class _FakePromoteResult:
    artifact_fingerprint: str
    directory: Path
    fold_id: int


def test_research_promote_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  promote:\n"
            "    run_id: '0123456789abcdef'\n"
        ),
    )
    calls: dict[str, object] = {}

    def fake_promote(request: object) -> _FakePromoteResult:
        calls["run_id"] = request.run_ref.run_id  # type: ignore[attr-defined]
        calls["storage_root"] = request.storage_root  # type: ignore[attr-defined]
        return _FakePromoteResult(
            artifact_fingerprint="f" * 64,
            directory=storage_root / "research" / "predictive_research" / "promoted" / ("f" * 64),
            fold_id=1,
        )

    with patch.object(research_cmd, "promote_predictive_run", fake_promote):
        exit_code = main(["research", "promote", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    assert calls["run_id"] == "0123456789abcdef"
    assert calls["storage_root"] == storage_root
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["artifact_fingerprint"] == "f" * 64
    assert result["fold_id"] == 1
    assert result["directory"].endswith("f" * 64)


def test_research_promote_dry_run_prints_plan_without_side_effect(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  promote:\n"
            "    run_id: '0123456789abcdef'\n"
        ),
    )

    exit_code = main(["research", "promote", "--config", str(config_path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["arguments"]["run_id"] == "0123456789abcdef"
    assert payload["plan"]["command"] == "promote"


def test_research_promote_missing_run_id_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="version: 1\nstorage_root: {storage_root}\n\nresearch:\n  promote:\n",
    )

    exit_code = main(["research", "promote", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


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


# ---------------------------------------------------------------------------
# `research run signal` (Sprint 064 T002, ADR-0026 Amendment 2, ADR-0038
# section 3). Like `research run strategy`, this never needs an ML extra, so
# it is exercised end to end against a real published dataset -- the CLI's
# own coverage is the seam (config -> loader -> resolve -> typed request ->
# typed result), not Signal Research's own analytics, which already has its
# own coverage under tests/unit/research/signal_research/.
# ---------------------------------------------------------------------------


def _write_signal_definition(path: Path, *, dataset_ref: str) -> None:
    definition_text = (
        "research_id: cli_research_run_signal_test\n"
        "research_scope: SIGNAL_MODEL_ONLY\n"
        f"dataset_ref: '{dataset_ref}'\n"
        "time_range:\n"
        "  start: '2018-12-31'\n"
        "  end: '2018-12-31'\n"
        "horizons:\n"
        "  - 5m\n"
        "signal_model: higher_low_long\n"
        "baseline:\n"
        "  type: AFTER_SIGNAL\n"
    )
    path.write_text(definition_text, encoding="utf-8")


def test_research_run_signal_end_to_end(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    definition_path = tmp_path / "signal_definition.yaml"
    _write_signal_definition(definition_path, dataset_ref=dataset_ref)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            f"    definition: {definition_path.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    # T005: 5 compact phase-event lines precede the pretty-printed result
    # blob in --json mode; see test_phase_events.py for their own coverage.
    payload = json.loads(_strip_phase_event_lines(capsys.readouterr().out))
    result = payload["result"]
    assert result["run_id"]
    assert result["research_id"] == "cli_research_run_signal_test"
    assert result["definition_hash"]


def test_research_run_signal_dry_run_has_no_side_effect(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR-0038 section 3: `--dry-run` performs no write anywhere under storage_root."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    definition_path = tmp_path / "signal_definition.yaml"
    _write_signal_definition(definition_path, dataset_ref=dataset_ref)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            f"    definition: {definition_path.as_posix()}\n"
        ),
    )
    research_root = storage_root / "research"
    files_before = (
        sorted(p.as_posix() for p in research_root.rglob("*")) if research_root.exists() else []
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    files_after = (
        sorted(p.as_posix() for p in research_root.rglob("*")) if research_root.exists() else []
    )
    assert files_after == files_before

    payload = json.loads(capsys.readouterr().out)
    plan_arguments = payload["plan"]["arguments"]
    assert plan_arguments["research_id"] == "cli_research_run_signal_test"
    assert plan_arguments["research_scope"] == "signal_model_only"
    assert plan_arguments["dataset_ref"] == dataset_ref
    assert plan_arguments["horizons"] == ["5m"]
    assert plan_arguments["signal_model_id"] == "higher_low_long"
    assert plan_arguments["definition_hash"]


def test_research_run_signal_round_trips_definition_hash(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR-0038 section 3's round-trip guarantee: --dry-run's definition_hash
    matches a real run's persisted definition_hash for the identical input."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    definition_path = tmp_path / "signal_definition.yaml"
    _write_signal_definition(definition_path, dataset_ref=dataset_ref)
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            f"    definition: {definition_path.as_posix()}\n"
        ),
    )

    dry_run_exit = main(["research", "run", "--config", str(config_path), "--dry-run", "--json"])
    dry_run_payload = json.loads(capsys.readouterr().out)
    assert dry_run_exit == EXIT_SUCCESS
    dry_run_hash = dry_run_payload["plan"]["arguments"]["definition_hash"]

    run_exit = main(["research", "run", "--config", str(config_path), "--json"])
    run_payload = json.loads(_strip_phase_event_lines(capsys.readouterr().out))
    assert run_exit == EXIT_SUCCESS
    assert run_payload["result"]["definition_hash"] == dry_run_hash


def test_research_run_signal_missing_definition_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=("version: 1\nstorage_root: {storage_root}\n\nresearch:\n  kind: signal\n"),
    )

    exit_code = main(["research", "run", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_research_run_signal_bad_definition_path_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    missing = tmp_path / "does_not_exist.yaml"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            f"    definition: {missing.as_posix()}\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run"])

    assert exit_code == EXIT_CONFIG_ERROR


def test_research_run_signal_unknown_config_key_names_offending_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            "    definition: does_not_matter.yaml\n"
            "    unknown_key: oops\n"
        ),
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run"])

    assert exit_code == EXIT_CONFIG_ERROR
    err = capsys.readouterr().err
    assert "unknown_key" in err
    assert "research.signal" in err
