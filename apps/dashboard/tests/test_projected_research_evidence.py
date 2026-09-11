"""Focused coverage for rich public Signal and Robustness evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from streamlit.testing.v1 import AppTest

from dashboard_app.publication.evidence import (
    SIGNAL_RESEARCH_EVIDENCE_ROLE,
    discover_research_evidence_inputs,
)
from dashboard_app.publication.generator import RawArtifactInput, build_projection_bundle
from dashboard_app.publication.paths import projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle,
    load_projection_bundle_from_path,
)
from dashboard_app.views.projected_research import (
    legacy_robustness_evidence,
    signal_research_evidence,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_evidence_sanitizers_drop_unknown_nested_fields(tmp_path: Path) -> None:
    inputs = _write_evidence_fixture(tmp_path)
    signal = next(item for item in inputs if item.artifact_role == SIGNAL_RESEARCH_EVIDENCE_ROLE)
    payload = dict(signal.raw_payload)
    tables = dict(payload["tables"])
    summary_rows = [dict(row) for row in tables["summary_metrics"]]
    summary_rows[0]["secret"] = "private"
    tables["summary_metrics"] = summary_rows
    tables["unknown_table"] = [{"secret": "private"}]
    payload["tables"] = tables
    payload["storage_path"] = "C:/private/run"
    inputs[inputs.index(signal)] = RawArtifactInput(
        artifact_id=signal.artifact_id,
        artifact_role=signal.artifact_role,
        raw_payload=payload,
    )

    bundle = build_projection_bundle(inputs, generated_at_utc=datetime(2026, 9, 11, tzinfo=UTC))
    projected = bundle.artifacts[signal.artifact_id].fields

    assert "storage_path" not in projected
    assert "secret" not in projected["tables"]["summary_metrics"][0]
    assert "unknown_table" not in projected["tables"]
    assert "private" not in repr(projected).lower()


def test_discovery_projects_signal_and_bounded_legacy_demo(tmp_path: Path) -> None:
    inputs = _write_evidence_fixture(tmp_path)
    bundle = build_projection_bundle(inputs, generated_at_utc=datetime(2026, 9, 11, tzinfo=UTC))

    signals = signal_research_evidence(bundle)
    robustness = legacy_robustness_evidence(bundle)

    assert len(signals) == 1
    signal_summary = signals[0].table("summary_metrics")
    assert signal_summary is not None
    assert signal_summary.num_rows == 1
    assert robustness is not None
    assert robustness.fields["evidence_label"] == "DEMO · LEGACY"
    equity = robustness.table("walk_forward_equity")
    assert equity is not None
    assert equity.num_rows == 1_200
    assert equity.column("equity")[0].as_py() == 0
    assert equity.column("equity")[-1].as_py() == 1_299
    assert all(item.artifact_role != "research_catalog_entry" for item in inputs)


def test_absent_optional_evidence_root_produces_no_inputs(tmp_path: Path) -> None:
    inputs, skipped = discover_research_evidence_inputs(tmp_path / "not-present")

    assert inputs == []
    assert skipped == 0


def test_pages_restore_rich_evidence_sections() -> None:
    signal_page = (_REPO_ROOT / "apps/dashboard/pages/4_Market_and_Signal_Research.py").read_text(
        encoding="utf-8"
    )
    robustness_page = (_REPO_ROOT / "apps/dashboard/pages/8_Robustness_Analysis.py").read_text(
        encoding="utf-8"
    )

    for heading in ("Summary metrics", "Grouped metrics", "Forward-return distributions"):
        assert heading in signal_page
    for heading in ("Walk-forward (IS/OOS)", "Parameter sweep", "Stress tests", "Monte Carlo"):
        assert heading in robustness_page
    assert "DEMO · LEGACY EVIDENCE" in robustness_page
    assert "list_runs" not in signal_page + robustness_page
    assert "storage_path" not in signal_page + robustness_page


def test_committed_projection_contains_rich_workflow_evidence() -> None:
    bundle = load_projection_bundle_from_path(projection_bundle_path())

    assert not isinstance(bundle, PublicationUnavailable)
    assert len(signal_research_evidence(bundle)) == 3
    assert legacy_robustness_evidence(bundle) is not None


def test_reader_rejects_unknown_nested_evidence_field() -> None:
    bundle = load_projection_bundle_from_path(projection_bundle_path())
    assert not isinstance(bundle, PublicationUnavailable)
    payload = bundle.to_dict()
    signal_id = next(
        artifact_id
        for artifact_id, artifact in bundle.artifacts.items()
        if artifact.artifact_role == SIGNAL_RESEARCH_EVIDENCE_ROLE
    )
    payload["artifacts"][signal_id]["fields"]["tables"]["summary_metrics"][0]["storage_path"] = (
        "C:/private/run"
    )

    result = load_projection_bundle(payload)

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "schema_mismatch"


def test_signal_page_renders_projected_tables_and_charts() -> None:
    app = AppTest.from_file(
        str(_REPO_ROOT / "apps/dashboard/pages/4_Market_and_Signal_Research.py")
    ).run(timeout=30)

    assert not app.exception
    assert any(item.value == "Summary metrics" for item in app.subheader)
    assert len(app.dataframe) >= 4
    assert len(app.get("plotly_chart")) >= 2


def test_robustness_page_renders_demo_verdict_and_analytics() -> None:
    app = AppTest.from_file(str(_REPO_ROOT / "apps/dashboard/pages/8_Robustness_Analysis.py")).run(
        timeout=30
    )

    assert not app.exception
    assert any("DEMO · LEGACY EVIDENCE" in item.value for item in app.warning)
    assert any(item.value == "Verdict: CONDITIONAL" for item in app.subheader)
    assert any(item.value == "Walk-forward (IS/OOS)" for item in app.subheader)
    assert len(app.checkbox) == 5
    assert len(app.get("plotly_chart")) >= 5


def _write_evidence_fixture(research_root: Path) -> list[RawArtifactInput]:
    signal_dir = research_root / "market_research/runs/signal-1"
    signal_analytics = signal_dir / "analytics"
    signal_analytics.mkdir(parents=True)
    (signal_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "signal-1",
                "schema_version": "signal_research.v2",
                "framework_version": "0.1.0",
                "created_at_utc": "2026-09-11T00:00:00+00:00",
                "source_dataset_ref": "NQ.c.0|ohlcv|1m|derived|demo@1",
                "evaluation_timeframe": "1m",
                "experiment_id": "signal-demo",
                "research_scope": "signal_model_only",
                "research_question": "Does the signal persist?",
            }
        ),
        encoding="utf-8",
    )
    pq.write_table(
        pa.table({"run_id": ["signal-1"], "horizon_bars": [5], "hit_rate": [0.5]}),
        signal_analytics / "summary_metrics.parquet",
    )

    robustness_dir = research_root / "strategy_robustness/experiments/demo-robustness-nq-half-year"
    robustness_analytics = robustness_dir / "analytics"
    robustness_analytics.mkdir(parents=True)
    (robustness_dir / "manifest.json").write_text(
        json.dumps(
            {
                "experiment_id": "demo-robustness-nq-half-year",
                "schema_version": "robustness_experiment.v1",
                "framework_version": "0.1.0",
                "created_at_utc": "2026-09-11T00:00:00+00:00",
                "spec": {
                    "dataset_ref": "NQ.c.0|ohlcv|1m|derived|demo@1",
                    "timeframe": "1m",
                    "strategy_template_id": "demo-template",
                },
            }
        ),
        encoding="utf-8",
    )
    (robustness_analytics / "verdict.json").write_text(
        json.dumps({"verdict": "CONDITIONAL", "gate_results": []}), encoding="utf-8"
    )
    pq.write_table(
        pa.table({"fold_index": [0], "train_net_pnl": [1.0], "oos_net_pnl": [0.5]}),
        robustness_analytics / "walk_forward_folds.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "observed_at": list(range(1_300)),
                "equity": list(range(1_300)),
                "drawdown": [0] * 1_300,
            }
        ),
        robustness_analytics / "walk_forward_equity.parquet",
    )
    inputs, skipped = discover_research_evidence_inputs(research_root)
    assert skipped == 0
    return inputs
