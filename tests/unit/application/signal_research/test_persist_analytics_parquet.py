"""Tests for Signal Research analytics Parquet dual-write."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import polars as pl

from tests.unit.application.signal_research.test_analytics_envelope import _sample_result
from tests.unit.research.datasets.test_signal_research_repository import _sample_envelope
from trading_framework.application.signal_research.analytics_parquet import (
    signal_analytics_parquet_tables,
)
from trading_framework.application.signal_research.persist_analytics import (
    persist_signal_research_analytics,
)
from trading_framework.infrastructure.storage.paths import (
    signal_research_analytics_parquet_path,
    signal_research_analytics_summary_path,
)
from trading_framework.research.datasets.signal_research import SignalResearchDatasetRepository


def test_signal_analytics_parquet_tables_include_summary_metrics() -> None:
    tables = signal_analytics_parquet_tables(_sample_result())
    assert "summary_metrics" in tables
    assert tables["summary_metrics"].height == 1
    assert tables["quality_warnings"].height == 1
    assert "conditional_comparison" in tables


def test_persist_signal_research_analytics_dual_writes_json_and_parquet(
    tmp_path: Path,
) -> None:
    run_id = "run-1"
    repo = SignalResearchDatasetRepository(tmp_path)
    repo.write(_sample_envelope(run_id=run_id))
    analytics = replace(_sample_result(), source_run_id=run_id)

    result = persist_signal_research_analytics(
        analytics,
        storage_root=tmp_path,
        repository=repo,
    )

    assert result.summary_path == signal_research_analytics_summary_path(tmp_path, run_id)
    assert result.summary_path.is_file()
    metrics_path = signal_research_analytics_parquet_path(tmp_path, run_id, "summary_metrics")
    assert metrics_path.is_file()
    assert metrics_path in result.parquet_paths
    loaded = pl.read_parquet(metrics_path)
    assert loaded.height == 1
    assert "forward_return_mean" in loaded.columns
    warnings = pl.read_parquet(
        signal_research_analytics_parquet_path(tmp_path, run_id, "quality_warnings")
    )
    assert warnings.height == 1
