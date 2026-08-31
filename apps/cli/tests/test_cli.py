"""Tests for the argparse tree, exit-code taxonomy, --dry-run and --json (S046-T001, T003)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trading_cli.cli import build_parser, main
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_WORKFLOW_FAILURE

_VALID_RESEARCH_CONFIG = """
version: 1
storage_root: {storage_root}

research:
  kind: predictive
  predictive:
    definition: configs/study.yaml
    estimator: configs/ridge.yaml
"""


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_help_lists_all_four_command_groups(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    for group in ("data", "research", "dry-run", "report"):
        assert group in out


def test_missing_subcommand_exits_with_config_error_code() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == EXIT_CONFIG_ERROR


def test_bad_flag_exits_with_config_error_code() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["research", "run", "--not-a-real-flag"])

    assert exc_info.value.code == EXIT_CONFIG_ERROR


def test_missing_config_file_returns_config_error_exit_code(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"

    exit_code = main(["research", "run", "--config", str(missing)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_invalid_config_returns_config_error_exit_code(tmp_path: Path) -> None:
    path = _write_config(tmp_path, "version: 1\nunknown_key: oops\n")

    exit_code = main(["research", "run", "--config", str(path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_not_implemented_command_returns_workflow_failure_exit_code(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    path = _write_config(
        tmp_path, _VALID_RESEARCH_CONFIG.format(storage_root=storage_root.as_posix())
    )

    exit_code = main(["research", "run", "--config", str(path)])

    assert exit_code == EXIT_WORKFLOW_FAILURE


def test_dry_run_returns_success_exit_code(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    path = _write_config(
        tmp_path, _VALID_RESEARCH_CONFIG.format(storage_root=storage_root.as_posix())
    )

    exit_code = main(["research", "run", "--config", str(path), "--dry-run"])

    assert exit_code == EXIT_SUCCESS


def test_dry_run_touches_nothing_on_disk(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    path = _write_config(
        tmp_path, _VALID_RESEARCH_CONFIG.format(storage_root=storage_root.as_posix())
    )
    before = _snapshot(tmp_path)

    exit_code = main(["research", "run", "--config", str(path), "--dry-run"])

    assert exit_code == EXIT_SUCCESS
    assert not storage_root.exists(), "dry-run must not create the storage root"
    assert _snapshot(tmp_path) == before, "dry-run must not modify any file under tmp_path"


def test_dry_run_prints_resolved_plan_as_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    path = _write_config(
        tmp_path, _VALID_RESEARCH_CONFIG.format(storage_root=storage_root.as_posix())
    )

    exit_code = main(["research", "run", "--config", str(path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "dry_run"
    assert payload["plan"]["group"] == "research"
    assert payload["plan"]["command"] == "run"
    assert payload["plan"]["workflow"] == "research.run.predictive"
    assert payload["plan"]["arguments"]["kind"] == "predictive"
    assert payload["plan"]["output_paths"]


def test_json_error_output_is_structured(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist.yaml"

    exit_code = main(["research", "run", "--config", str(missing), "--json"])

    assert exit_code == EXIT_CONFIG_ERROR
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "error"
    assert payload["exit_code"] == EXIT_CONFIG_ERROR
    assert "does-not-exist.yaml" in payload["message"]


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}
