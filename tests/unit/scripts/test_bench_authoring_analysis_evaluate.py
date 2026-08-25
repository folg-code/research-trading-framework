"""Smoke test for the authoring → analysis → evaluate microbench."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.ops.bench_authoring_analysis_evaluate import main

_REPO_ROOT = Path(__file__).resolve().parents[3]
_USER_DATA = _REPO_ROOT / "user_data"
_P3_EVALUATION_PHASES = (
    "evaluate_models.validate",
    "evaluate_models.collect_dependencies",
    "evaluate_models.build_evaluation_table",
    "evaluate_models.market_models",
    "evaluate_models.signal_models",
)
_NESTED_ANALYSIS_PHASE = "evaluate_models.run_analysis"


def _user_data_shallow_entries() -> frozenset[str]:
    if not _USER_DATA.exists():
        return frozenset()
    entries: set[str] = set()
    for path in _USER_DATA.iterdir():
        entries.add(path.name)
        if path.is_dir():
            for child in path.iterdir():
                entries.add(f"{path.name}/{child.name}")
    return frozenset(entries)


def test_bench_authoring_analysis_evaluate_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--bars", "80"]) == 0
    output = capsys.readouterr().out
    assert "p1_compile" in output
    assert "p2_run_analysis" in output
    assert "p3_evaluate" in output


def test_bench_authoring_analysis_evaluate_json_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before_user_data = _user_data_shallow_entries()
    assert main(["--bars", "80", "--json"]) == 0
    assert _user_data_shallow_entries() == before_user_data

    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {
        "bar_count",
        "market_model_ids",
        "signal_model_ids",
        "phases",
        "nested_phases",
        "notes",
    }
    phase_names = [item["name"] for item in payload["phases"]]
    assert phase_names == ["p1_compile", "p2_run_analysis", "p3_evaluate"]
    assert payload["bar_count"] == 80
    assert payload["market_model_ids"] == ["high_volatility"]
    assert payload["signal_model_ids"] == ["high_volatility_long_edge"]
    for item in payload["phases"]:
        assert set(item) == {"name", "wall_seconds", "peak_bytes"}
        assert item["wall_seconds"] >= 0.0
        assert isinstance(item["peak_bytes"], int)
        assert item["peak_bytes"] >= 0
    p2 = next(item for item in payload["phases"] if item["name"] == "p2_run_analysis")
    p3 = next(item for item in payload["phases"] if item["name"] == "p3_evaluate")
    assert p2["wall_seconds"] > 0.0
    assert p3["wall_seconds"] > 0.0

    nested_by_name = {item["name"]: item for item in payload["nested_phases"]}
    assert _NESTED_ANALYSIS_PHASE in nested_by_name
    nested_analysis = nested_by_name[_NESTED_ANALYSIS_PHASE]
    assert nested_analysis["inclusive_seconds"] > 0.0
    assert nested_analysis["call_count"] >= 1
    missing_p3_phases = [name for name in _P3_EVALUATION_PHASES if name not in nested_by_name]
    assert missing_p3_phases == []
    expected_p3 = sum(nested_by_name[name]["inclusive_seconds"] for name in _P3_EVALUATION_PHASES)
    assert p3["wall_seconds"] == pytest.approx(expected_p3)
    assert p3["wall_seconds"] != pytest.approx(expected_p3 + nested_analysis["inclusive_seconds"])
    notes = " ".join(payload["notes"]).lower()
    assert "user_data" in notes
    assert "nested" in notes and "run_analysis" in notes


@pytest.mark.parametrize("bars", ["1", "0", "-5"])
def test_bench_authoring_analysis_evaluate_rejects_too_few_bars(
    capsys: pytest.CaptureFixture[str],
    bars: str,
) -> None:
    assert main(["--bars", bars]) == 1
    assert "bars must be >=" in capsys.readouterr().out
