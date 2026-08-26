"""Tests for Predictive Research HTML report orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.research.reporting.predictive.test_view_model import _source_report
from trading_framework.application.predictive_research import (
    RenderPredictiveReportError,
    RenderPredictiveReportRequest,
    render_predictive_research_report,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_metrics_path,
    predictive_research_run_report_path,
)
from trading_framework.research.datasets.predictive import PredictiveDatasetRepository
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.clocks.system import SystemClock


def _persist_source(storage_root: Path) -> PredictiveReportSource:
    source = _source_report()
    PredictiveDatasetRepository(storage_root).write(source.dataset)
    PredictiveRunRepository(storage_root).write(source.run, model_blobs={})
    metrics_path = predictive_research_run_metrics_path(storage_root, source.run.manifest.run_id)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(source.metrics.to_dict(), indent=2), encoding="utf-8")
    return source


def test_render_writes_report_next_to_persisted_run(tmp_path: Path) -> None:
    source = _persist_source(tmp_path)
    result = render_predictive_research_report(
        RenderPredictiveReportRequest(
            run_ref=PredictiveRunRef(run_id=source.run.manifest.run_id),
            storage_root=tmp_path,
            clock=FixedClock(source.run.manifest.created_at_utc),
        )
    )
    expected = predictive_research_run_report_path(tmp_path, source.run.manifest.run_id)
    assert result.output_path == expected
    assert expected.is_file()
    document = expected.read_text(encoding="utf-8")
    assert 'src="https://cdn.plot.ly' not in document
    assert source.run.manifest.run_id in document


def test_render_requires_persisted_metrics(tmp_path: Path) -> None:
    source = _source_report()
    PredictiveDatasetRepository(tmp_path).write(source.dataset)
    PredictiveRunRepository(tmp_path).write(source.run, model_blobs={})
    with pytest.raises(RenderPredictiveReportError, match=r"metrics\.json not found"):
        render_predictive_research_report(
            RenderPredictiveReportRequest(
                run_ref=PredictiveRunRef(run_id=source.run.manifest.run_id),
                storage_root=tmp_path,
                clock=SystemClock(),
            )
        )
