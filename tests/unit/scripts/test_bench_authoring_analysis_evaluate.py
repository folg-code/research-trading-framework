"""Smoke test for the authoring → analysis → evaluate microbench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
_REPORT_KEYS = {
    "bar_count",
    "market_model_ids",
    "signal_model_ids",
    "phases",
    "nested_phases",
    "notes",
    "mtf",
    "parquet",
}


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


def _assert_core_json_report(
    payload: dict[str, Any],
    *,
    bar_count: int,
    mtf: bool,
    parquet: bool,
) -> dict[str, Any]:
    assert set(payload) == _REPORT_KEYS
    assert payload["bar_count"] == bar_count
    assert payload["mtf"] is mtf
    assert payload["parquet"] is parquet
    for item in payload["phases"]:
        assert set(item) == {"name", "wall_seconds", "peak_bytes"}
        assert item["wall_seconds"] >= 0.0
        assert isinstance(item["peak_bytes"], int)
        assert item["peak_bytes"] >= 0
    nested_by_name = {item["name"]: item for item in payload["nested_phases"]}
    assert _NESTED_ANALYSIS_PHASE in nested_by_name
    missing_p3_phases = [name for name in _P3_EVALUATION_PHASES if name not in nested_by_name]
    assert missing_p3_phases == []
    return nested_by_name


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
    nested_by_name = _assert_core_json_report(payload, bar_count=80, mtf=False, parquet=False)
    phase_names = [item["name"] for item in payload["phases"]]
    assert phase_names == ["p1_compile", "p2_run_analysis", "p3_evaluate"]
    assert payload["market_model_ids"] == ["high_volatility"]
    assert payload["signal_model_ids"] == ["high_volatility_long_edge"]
    p2 = next(item for item in payload["phases"] if item["name"] == "p2_run_analysis")
    p3 = next(item for item in payload["phases"] if item["name"] == "p3_evaluate")
    assert p2["wall_seconds"] > 0.0
    assert p3["wall_seconds"] > 0.0

    nested_analysis = nested_by_name[_NESTED_ANALYSIS_PHASE]
    assert nested_analysis["inclusive_seconds"] > 0.0
    assert nested_analysis["call_count"] >= 1
    expected_p3 = sum(nested_by_name[name]["inclusive_seconds"] for name in _P3_EVALUATION_PHASES)
    assert p3["wall_seconds"] == pytest.approx(expected_p3)
    assert p3["wall_seconds"] != pytest.approx(expected_p3 + nested_analysis["inclusive_seconds"])
    notes = " ".join(payload["notes"]).lower()
    assert "user_data" in notes
    assert "nested" in notes and "run_analysis" in notes
    assert not any(name.startswith("execute.resample.") for name in nested_by_name)
    assert not any(name.startswith("ohlcv.") for name in nested_by_name)


def test_bench_authoring_analysis_evaluate_mtf_json_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before_user_data = _user_data_shallow_entries()
    assert main(["--bars", "80", "--json", "--mtf"]) == 0
    assert _user_data_shallow_entries() == before_user_data

    payload = json.loads(capsys.readouterr().out)
    nested_by_name = _assert_core_json_report(payload, bar_count=80, mtf=True, parquet=False)
    notes = " ".join(payload["notes"]).lower()
    assert "mtf" in notes
    assert "resample" in notes
    resample_phases = [name for name in nested_by_name if name.startswith("execute.resample.")]
    align_phases = [name for name in nested_by_name if name.startswith("align.")]
    assert resample_phases
    assert align_phases
    assert nested_by_name[resample_phases[0]]["inclusive_seconds"] > 0.0
    assert nested_by_name[align_phases[0]]["inclusive_seconds"] > 0.0


def test_bench_authoring_analysis_evaluate_parquet_json_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before_user_data = _user_data_shallow_entries()
    assert main(["--bars", "80", "--json", "--parquet"]) == 0
    assert _user_data_shallow_entries() == before_user_data

    payload = json.loads(capsys.readouterr().out)
    nested_by_name = _assert_core_json_report(payload, bar_count=80, mtf=False, parquet=True)
    notes = " ".join(payload["notes"]).lower()
    assert "parquet" in notes
    assert "user_data" in notes
    parquet_read_phases = [
        name
        for name in nested_by_name
        if name.startswith("ohlcv.") or name == "load_market_view.query_columnar"
    ]
    assert parquet_read_phases
    assert any(nested_by_name[name]["inclusive_seconds"] > 0.0 for name in parquet_read_phases)
    assert "load_market_view.query_columnar" in nested_by_name
    assert "load_market_view.from_preloaded_columnar" not in nested_by_name


@pytest.mark.parametrize("bars", ["1", "0", "-5"])
def test_bench_authoring_analysis_evaluate_rejects_too_few_bars(
    capsys: pytest.CaptureFixture[str],
    bars: str,
) -> None:
    assert main(["--bars", bars]) == 1
    assert "bars must be >=" in capsys.readouterr().out
