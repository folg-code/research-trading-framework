"""Smoke test for the authoring → analysis → evaluate microbench."""

from __future__ import annotations

import json

import pytest
from scripts.ops.bench_authoring_analysis_evaluate import main


def test_bench_authoring_analysis_evaluate_smoke() -> None:
    assert main(["--bars", "80"]) == 0


def test_bench_authoring_analysis_evaluate_json_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--bars", "80", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    phase_names = [item["name"] for item in payload["phases"]]
    assert phase_names == ["p1_compile", "p2_run_analysis", "p3_evaluate"]
    assert payload["bar_count"] == 80
    assert payload["market_model_ids"] == ["high_volatility"]
    assert payload["signal_model_ids"] == ["high_volatility_long_edge"]
    assert all(item["wall_seconds"] >= 0.0 for item in payload["phases"])


def test_bench_authoring_analysis_evaluate_rejects_too_few_bars(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--bars", "1"]) == 1
    assert "bars must be >=" in capsys.readouterr().out
