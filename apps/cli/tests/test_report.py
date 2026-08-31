"""Tests for `trading-cli report render` (S046-T005).

Tier 1, network-free. The wrapped application workflows already have their
own coverage (predictive_research/strategy_research test suites); these tests
exercise the seam -- config -> ResolvedPlan -> typed request -> printed
result -- by faking the two application-layer entry points, following the
project's established CLI-test pattern (see
tests/unit/scripts/test_btc_futures_dry_run_cli.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from trading_framework.core.exceptions import ValidationError

from trading_cli.cli import main
from trading_cli.commands import report as report_cmd
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_WORKFLOW_FAILURE


def _write_config(tmp_path: Path, *, storage_root: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text.format(storage_root=storage_root.as_posix()), encoding="utf-8")
    return path


@dataclass(frozen=True, slots=True)
class _FakePredictiveRenderResult:
    run_id: str
    output_path: Path


def test_report_render_predictive_calls_application_workflow(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="""
version: 1
storage_root: {storage_root}

report:
  kind: predictive
  run_id: run-123
""",
    )
    captured: dict[str, object] = {}

    def fake_render(request: object) -> _FakePredictiveRenderResult:
        captured["run_id"] = request.run_ref.run_id  # type: ignore[attr-defined]
        captured["storage_root"] = request.storage_root  # type: ignore[attr-defined]
        captured["output_path"] = request.output_path  # type: ignore[attr-defined]
        return _FakePredictiveRenderResult(run_id="run-123", output_path=Path("report.html"))

    with patch.object(report_cmd, "render_predictive_research_report", fake_render):
        exit_code = main(["report", "render", "--config", str(config_path)])

    assert exit_code == EXIT_SUCCESS
    assert captured["run_id"] == "run-123"
    assert captured["storage_root"] == storage_root
    assert captured["output_path"] is None


@dataclass(frozen=True, slots=True)
class _FakeOverview:
    trade_count: int


@dataclass(frozen=True, slots=True)
class _FakeViewModel:
    overview: _FakeOverview


def test_report_render_strategy_uses_default_output_path_and_prints_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="""
version: 1
storage_root: {storage_root}

report:
  kind: strategy
  run_id: strat-run-1
""",
    )

    def fake_build(request: object) -> _FakeViewModel:
        return _FakeViewModel(overview=_FakeOverview(trade_count=7))

    captured: dict[str, object] = {}

    def fake_render(view_model: _FakeViewModel, output_path: Path) -> Path:
        captured["output_path"] = output_path
        return output_path

    with (
        patch.object(report_cmd, "build_strategy_dashboard_view_model", fake_build),
        patch.object(report_cmd, "render_strategy_research_dashboard", fake_render),
    ):
        exit_code = main(["report", "render", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    expected_output = storage_root / "reports" / "strategy" / "strat-run-1.html"
    assert captured["output_path"] == expected_output
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["trade_count"] == 7
    assert payload["result"]["output_path"] == str(expected_output)


def test_report_render_missing_run_returns_workflow_failure_exit_code(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="""
version: 1
storage_root: {storage_root}

report:
  kind: predictive
  run_id: does-not-exist
""",
    )

    def fake_render(request: object) -> _FakePredictiveRenderResult:
        raise ValidationError("run not found: does-not-exist")

    with patch.object(report_cmd, "render_predictive_research_report", fake_render):
        exit_code = main(["report", "render", "--config", str(config_path)])

    assert exit_code == EXIT_WORKFLOW_FAILURE


def test_report_render_missing_run_id_returns_config_error_exit_code(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text="""
version: 1
storage_root: {storage_root}

report:
  kind: predictive
""",
    )

    exit_code = main(["report", "render", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR
