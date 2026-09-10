"""Acceptance tests for projection-only workflow evidence pages 2-4."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.catalog_index import PublicCatalogRun
from dashboard_app.publication.projection import ProjectedArtifact, PublicProjectionBundle
from dashboard_app.views.workflow_evidence import (
    projected_role_fields_for_run,
    representative_dataset_evidence,
    runs_for_workflow,
)

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
_PAGE_PATHS = (
    "2_Market_and_Signal_Research.py",
    "3_Strategy_Research.py",
    "4_Robustness_Analysis.py",
)


def _run(workflow: WorkflowKind = WorkflowKind.SIGNAL) -> PublicCatalogRun:
    return PublicCatalogRun(
        artifact_id=f"catalog-{workflow.value}-run-1",
        workflow=workflow,
        run_id="run-1",
        title=f"{workflow.value.title()} · model-1",
        created_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        source_dataset_ref="BTCUSDT.P|ohlcv|1m|binance|klines@1",
        evaluation_timeframe="1m",
        framework_version="0.1.0",
        artifact_schema_version="research.v1",
        research_scope="SIGNAL_MODEL_ONLY",
        experiment_id="experiment-1",
        time_range_start_utc=datetime(2024, 1, 1, tzinfo=UTC),
        time_range_end_utc=datetime(2024, 6, 30, tzinfo=UTC),
        verdict=None,
    )


def test_workflow_helpers_copy_identity_and_explicit_projected_role() -> None:
    signal = _run()
    strategy = _run(WorkflowKind.STRATEGY)
    artifact = ProjectedArtifact(
        artifact_id="strategy-research-run-run-1",
        artifact_role="strategy_research_run_summary",
        fields={"run_id": "run-1", "trade_count": 42},
    )
    bundle = PublicProjectionBundle(
        schema_version="dashboard.public.v1",
        generator_version="test",
        generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        artifacts={artifact.artifact_id: artifact},
    )

    dataset = representative_dataset_evidence([signal, strategy])

    assert dataset is not None
    assert dataset.source_dataset_ref == signal.source_dataset_ref
    assert dataset.referenced_by_run_id == "run-1"
    assert runs_for_workflow([signal, strategy], WorkflowKind.STRATEGY) == (strategy,)
    assert projected_role_fields_for_run(
        bundle,
        artifact_role="strategy_research_run_summary",
        run_id="run-1",
    ) == {"run_id": "run-1", "trade_count": 42}


def test_pages_2_to_4_render_without_private_storage() -> None:
    app = AppTest.from_file(str(_DASHBOARD_ROOT / "Project_Overview.py"))
    app.run(timeout=30)

    expected_titles = (
        "Market Data and Signal Research Evidence",
        "Strategy Research Evidence",
        "Robustness Research Evidence",
    )
    for page, expected in zip(_PAGE_PATHS, expected_titles, strict=True):
        app.switch_page(f"pages/{page}")
        app.run(timeout=30)
        assert not app.exception
        assert app.title[0].value == expected


def test_pages_2_to_4_have_no_workspace_or_scanner_read_path() -> None:
    forbidden = (
        "DASHBOARD_STORAGE_ROOT",
        "settings.storage_root",
        "DashboardQueryService",
        "storage_path",
        "file://",
        "cached_list_runs",
        "list_research_runs",
        "list_strategy_runs",
        "list_robustness_experiments",
    )
    for name in _PAGE_PATHS:
        source = (_DASHBOARD_ROOT / "pages" / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def test_robustness_page_does_not_publish_legacy_demo_as_evidence() -> None:
    source = (_DASHBOARD_ROOT / "pages" / "4_Robustness_Analysis.py").read_text(encoding="utf-8")

    assert "demo-robustness-nq-half-year" not in source
    assert "Legacy demo-robustness artifacts are intentionally not presented" in source
