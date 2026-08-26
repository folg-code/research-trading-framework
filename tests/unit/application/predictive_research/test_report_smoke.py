"""Smoke tests: regression and classification Predictive Research HTML reports."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tests.unit.research.reporting.predictive.test_view_model import _source_report
from trading_framework.application.predictive_research import (
    RenderPredictiveReportRequest,
    render_predictive_research_report,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_metrics_path
from trading_framework.research.datasets.predictive import PredictiveDatasetRepository
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.reporting.predictive.contracts import PredictiveReportSource
from trading_framework.time.clocks.fixed import FixedClock


def _persist(storage_root: Path, source: PredictiveReportSource) -> str:
    PredictiveDatasetRepository(storage_root).write(source.dataset)
    PredictiveRunRepository(storage_root).write(source.run, model_blobs={})
    metrics_path = predictive_research_run_metrics_path(storage_root, source.run.manifest.run_id)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(source.metrics.to_dict(), indent=2), encoding="utf-8")
    return source.run.manifest.run_id


def _render(storage_root: Path, run_id: str, generated_at: datetime) -> str:
    result = render_predictive_research_report(
        RenderPredictiveReportRequest(
            run_ref=PredictiveRunRef(run_id=run_id),
            storage_root=storage_root,
            clock=FixedClock(generated_at),
        )
    )
    return result.output_path.read_text(encoding="utf-8")


def _section(document: str, panel_id: str) -> str:
    start = document.index(f'id="{panel_id}"')
    next_section = document.find("<section", start + 1)
    return document[start:] if next_section < 0 else document[start:next_section]


def test_regression_report_smoke_renders_quality_and_skips_classification_panels(
    tmp_path: Path,
) -> None:
    source = _source_report()
    document = _render(tmp_path, _persist(tmp_path, source), source.run.manifest.created_at_utc)
    assert 'src="https://cdn.plot.ly' not in document
    assert "chart-block" in _section(document, "fold_timeline")
    assert "chart-block" in _section(document, "prediction_quality")
    assert "chart-block" in _section(document, "prediction_buckets")
    assert "Skipped" in _section(document, "discrimination")
    assert "Skipped" in _section(document, "calibration")
    assert "Quality flags" in document


def test_classification_report_smoke_renders_calibration_when_probabilities_exist(
    tmp_path: Path,
) -> None:
    source = _source_report(binary=True, with_proba=True)
    document = _render(tmp_path, _persist(tmp_path, source), source.run.manifest.created_at_utc)
    assert 'src="https://cdn.plot.ly' not in document
    assert "chart-block" in _section(document, "discrimination")
    assert "chart-block" in _section(document, "calibration")
    assert "Skipped" in _section(document, "prediction_quality")
    assert "probabilities" not in _section(document, "calibration")


def test_classification_report_smoke_skips_calibration_without_probabilities(
    tmp_path: Path,
) -> None:
    source = _source_report(binary=True, with_proba=False)
    document = _render(tmp_path, _persist(tmp_path, source), source.run.manifest.created_at_utc)
    calibration = _section(document, "calibration")
    assert "chart-block" not in calibration
    assert "probabilities" in calibration
    assert "Skipped" in calibration
