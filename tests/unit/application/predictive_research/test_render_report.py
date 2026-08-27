"""Tests for Predictive Research HTML report orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.research.reporting.predictive.test_view_model import (
    _importance_trace,
    _leaderboard,
    _learning_curves,
    _selection_trace,
    _source_report,
    _window_accounting,
)
from trading_framework.application.predictive_research import (
    RenderPredictiveReportError,
    RenderPredictiveReportRequest,
    render_predictive_research_report,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_importance_path,
    predictive_research_run_leaderboard_path,
    predictive_research_run_learning_curves_path,
    predictive_research_run_metrics_path,
    predictive_research_run_report_path,
    predictive_research_run_selection_path,
    predictive_research_run_window_accounting_path,
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


def test_render_loads_optional_tree_sidecars(tmp_path: Path) -> None:
    source = _source_report(
        importance=_importance_trace(native=True),
        selection=_selection_trace(),
        leaderboard=_leaderboard(),
        fold_primary={
            "0": {"train_primary": 0.9, "test_primary": 0.4, "primary_gap": 0.5},
        },
    )
    PredictiveDatasetRepository(tmp_path).write(source.dataset)
    PredictiveRunRepository(tmp_path).write(source.run, model_blobs={})
    run_id = source.run.manifest.run_id
    metrics_path = predictive_research_run_metrics_path(tmp_path, run_id)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(source.metrics.to_dict(), indent=2), encoding="utf-8")
    assert source.importance is not None
    assert source.selection is not None
    assert source.leaderboard is not None
    predictive_research_run_importance_path(tmp_path, run_id).write_text(
        json.dumps(source.importance.to_dict()), encoding="utf-8"
    )
    predictive_research_run_selection_path(tmp_path, run_id).write_text(
        json.dumps(source.selection.to_dict()), encoding="utf-8"
    )
    predictive_research_run_leaderboard_path(tmp_path, run_id).write_text(
        json.dumps(source.leaderboard.to_dict()), encoding="utf-8"
    )
    result = render_predictive_research_report(
        RenderPredictiveReportRequest(
            run_ref=PredictiveRunRef(run_id=run_id),
            storage_root=tmp_path,
            clock=FixedClock(source.run.manifest.created_at_utc),
        )
    )
    document = result.output_path.read_text(encoding="utf-8")
    assert "Native gain is a training-fold statistic" in document
    assert "chart-block" in document
    assert "Skipped: no importance.json" not in document
    assert "Skipped: no leaderboard.json" not in document
    assert "Skipped: no selection.json" not in document


def test_render_loads_optional_neural_sidecars(tmp_path: Path) -> None:
    source = _source_report(
        learning_curves=_learning_curves(),
        window_accounting=_window_accounting(),
    )
    PredictiveDatasetRepository(tmp_path).write(source.dataset)
    PredictiveRunRepository(tmp_path).write(source.run, model_blobs={})
    run_id = source.run.manifest.run_id
    metrics_path = predictive_research_run_metrics_path(tmp_path, run_id)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(source.metrics.to_dict(), indent=2), encoding="utf-8")
    assert source.learning_curves is not None
    assert source.window_accounting is not None
    predictive_research_run_learning_curves_path(tmp_path, run_id).write_text(
        json.dumps(source.learning_curves.to_dict()), encoding="utf-8"
    )
    predictive_research_run_window_accounting_path(tmp_path, run_id).write_text(
        json.dumps(source.window_accounting.to_dict()), encoding="utf-8"
    )
    result = render_predictive_research_report(
        RenderPredictiveReportRequest(
            run_ref=PredictiveRunRef(run_id=run_id),
            storage_root=tmp_path,
            clock=FixedClock(source.run.manifest.created_at_utc),
        )
    )
    document = result.output_path.read_text(encoding="utf-8")
    assert "inner early-stopping run" in document
    assert "Skipped: no learning_curves.json" not in document
    assert "Skipped: no window_accounting.json" not in document
