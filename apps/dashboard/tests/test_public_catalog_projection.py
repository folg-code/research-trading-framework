"""Sprint 061 T005 tests for generalized public catalog projection."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, RunSummary, WorkflowKind
from dashboard_app.publication.catalog import (
    RESEARCH_CATALOG_ENTRY_ROLE,
    build_catalog_artifact_input,
)
from dashboard_app.publication.errors import (
    DuplicateArtifactIdError,
    InvalidProjectionSchemaError,
    UnsafePublicIdentityError,
)
from dashboard_app.publication.generator import (
    RawArtifactInput,
    build_projection_bundle,
    extend_projection_bundle,
)
from dashboard_app.publication.projection import (
    PUBLIC_PROJECTION_SCHEMA_VERSION,
    ProjectedArtifact,
    PublicProjectionBundle,
)
from dashboard_app.publication.workspace import discover_catalog_inputs


def _summary(
    workflow: WorkflowKind = WorkflowKind.STRATEGY,
    *,
    run_id: str = "run-1",
) -> RunSummary:
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=workflow,
        run_id=run_id,
        created_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        title=f"{workflow.value.title()} · model-1",
        storage_path="C:/private/user_data/workspace/research/run-1",
        source_dataset_ref="BTCUSDT.P|ohlcv|1m|binance|klines@1",
        evaluation_timeframe="1m",
        framework_version="0.1.0",
        artifact_schema_version="research.v1",
        experiment_id="experiment-1",
        time_range_start_utc=datetime(2024, 1, 1, tzinfo=UTC),
        time_range_end_utc=datetime(2024, 6, 30, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    "workflow",
    [
        WorkflowKind.MARKET,
        WorkflowKind.SIGNAL,
        WorkflowKind.STRATEGY,
        WorkflowKind.ROBUSTNESS,
        WorkflowKind.PREDICTIVE,
    ],
)
def test_catalog_entry_supports_every_research_workflow_without_paths(
    workflow: WorkflowKind,
) -> None:
    raw = build_catalog_artifact_input(_summary(workflow), verdict="INCONCLUSIVE")
    bundle = build_projection_bundle([raw], generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC))

    artifact = bundle.artifacts[f"catalog-{workflow.value}-run-1"]
    assert artifact.artifact_role == RESEARCH_CATALOG_ENTRY_ROLE
    assert artifact.fields["workflow"] == workflow.value
    assert artifact.fields["verdict"] == "INCONCLUSIVE"
    assert artifact.fields["time_range_start_utc"] == "2024-01-01T00:00:00+00:00"
    assert "storage_path" not in artifact.fields
    assert "private" not in repr(artifact.fields)


@pytest.mark.parametrize(
    ("summary", "verdict"),
    [
        (_summary(run_id="../private"), None),
        (_summary(WorkflowKind.LIVE_PAPER), None),
        (_summary(), "C:\\private\\verdict.json"),
    ],
)
def test_catalog_entry_rejects_unsafe_or_unsupported_identity(
    summary: RunSummary,
    verdict: str | None,
) -> None:
    with pytest.raises(UnsafePublicIdentityError):
        build_catalog_artifact_input(summary, verdict=verdict)


def test_catalog_entry_rejects_naive_timestamp() -> None:
    summary = replace(_summary(), created_at_utc=datetime(2026, 9, 10))

    with pytest.raises(UnsafePublicIdentityError, match="timezone-aware"):
        build_catalog_artifact_input(summary)


def test_catalog_sanitizer_rejects_bypass_with_path_like_field() -> None:
    with pytest.raises(UnsafePublicIdentityError, match="source_dataset_ref"):
        build_projection_bundle(
            [
                RawArtifactInput(
                    artifact_id="catalog-strategy-safe",
                    artifact_role=RESEARCH_CATALOG_ENTRY_ROLE,
                    raw_payload={
                        "workflow": "strategy",
                        "run_id": "safe",
                        "title": "Strategy",
                        "source_dataset_ref": "C:\\private\\dataset",
                    },
                )
            ],
            generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        )


def test_generator_rejects_duplicate_catalog_artifact_ids() -> None:
    raw = build_catalog_artifact_input(_summary())

    with pytest.raises(DuplicateArtifactIdError):
        build_projection_bundle([raw, raw], generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC))


def test_extension_rejects_collision_with_base_bundle() -> None:
    raw = build_catalog_artifact_input(_summary())
    base = build_projection_bundle([raw], generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC))

    with pytest.raises(DuplicateArtifactIdError):
        extend_projection_bundle(
            base,
            [raw],
            generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
        )


def test_projection_reader_rejects_path_like_or_mismatched_artifact_identity() -> None:
    with pytest.raises(InvalidProjectionSchemaError, match="unsafe public artifact_id"):
        ProjectedArtifact(
            artifact_id="../private",
            artifact_role=RESEARCH_CATALOG_ENTRY_ROLE,
            fields={},
        )

    artifact = ProjectedArtifact(
        artifact_id="catalog-strategy-safe-run",
        artifact_role=RESEARCH_CATALOG_ENTRY_ROLE,
        fields={},
    )
    with pytest.raises(InvalidProjectionSchemaError, match="does not match"):
        PublicProjectionBundle(
            schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
            generator_version="test",
            generated_at_utc=datetime(2026, 9, 10, tzinfo=UTC),
            artifacts={"different-key": artifact},
        )


def test_workspace_discovery_projects_safe_runs_and_skips_corrupt(tmp_path: Path) -> None:
    runs = tmp_path / "research" / "strategy_research" / "runs"
    safe = runs / "safe"
    safe.mkdir(parents=True)
    (safe / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "safe-run",
                "schema_version": "strategy_research.v1",
                "created_at_utc": "2026-09-10T00:00:00+00:00",
                "source_dataset_ref": "BTCUSDT.P|ohlcv|1m|binance|klines@1",
                "evaluation_timeframe": "1m",
                "strategy_model_id": "model-1",
            }
        ),
        encoding="utf-8",
    )
    corrupt = runs / "corrupt"
    corrupt.mkdir()
    (corrupt / "manifest.json").write_text("{not-json", encoding="utf-8")

    inputs, skipped = discover_catalog_inputs(tmp_path)

    assert [item.artifact_id for item in inputs] == ["catalog-strategy-safe-run"]
    assert skipped == 1
