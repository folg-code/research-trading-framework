"""Tests for human-readable catalog run picker labels."""

from __future__ import annotations

from datetime import UTC, datetime

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, RunSummary, WorkflowKind
from dashboard_app.views.picker import format_run_label, run_picker_options


def _summary(**overrides: object) -> RunSummary:
    payload: dict[str, object] = {
        "schema_version": PRESENTATION_SCHEMA_VERSION,
        "workflow": WorkflowKind.STRATEGY,
        "run_id": "opaque-uuid-1",
        "created_at_utc": datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
        "title": "Strategy · demo",
        "storage_path": "/tmp/x",
        "source_dataset_ref": "NQ@continuous",
        "evaluation_timeframe": "5m",
    }
    payload.update(overrides)
    return RunSummary(**payload)  # type: ignore[arg-type]


def test_format_run_label_leads_with_date_and_title_not_run_id() -> None:
    label = format_run_label(_summary())
    assert label.startswith("2026-07-18")
    assert "Strategy · demo" in label
    assert "NQ continuous · 5m" in label
    assert "opaque-uuid-1" not in label


def test_run_picker_options_disambiguates_duplicate_labels() -> None:
    a = _summary(run_id="aaa")
    b = _summary(run_id="bbb")
    options = run_picker_options((a, b))
    assert len(options) == 2
    assert any("#aaa" in key for key in options)
    assert any("#bbb" in key for key in options)
