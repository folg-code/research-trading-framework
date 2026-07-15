"""Unit tests for Model Research NQ demo script."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.demo import run_model_research_nq_demo


def test_model_research_nq_demo_fixture_generates_index_and_scope_reports(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    pytest.importorskip("plotly")
    del ohlcv_sample_1m_path  # fixture path is resolved inside the demo module

    storage_root = tmp_path / "storage"
    output_index = tmp_path / "output" / "08_model_research_nq_half_year.html"
    scope_output_dir = tmp_path / "output" / "model_research"

    exit_code = run_model_research_nq_demo.main(
        [
            "--fixture",
            "--storage-root",
            str(storage_root),
            "--output",
            str(output_index),
            "--scope-output-dir",
            str(scope_output_dir),
            "--refresh-runs",
        ]
    )
    assert exit_code == 0
    assert output_index.is_file()
    index_html = output_index.read_text(encoding="utf-8")
    assert "Model Research Methodology" in index_html

    for filename in (
        "signal_model_only.html",
        "market_and_signal.html",
    ):
        report_path = scope_output_dir / filename
        assert report_path.is_file(), filename
        assert "plotly" in report_path.read_text(encoding="utf-8").lower()
