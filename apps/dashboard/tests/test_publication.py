"""Tests for the public projection + study-manifest publication boundary.

Sprint 059 T002 / ADR-0034. Fixtures use plain dict literals shaped like the
two representative real artifacts: a persisted predictive-run
``verdict.json`` (rich, nested) and a promoted-artifact ``manifest.json``
(a degenerate, scalar-only identity). Each fixture also carries fields that
must never survive sanitization: a ``storage_path``, a nested ``config``
dict, a ``hostname``, and an unlisted-but-plausible key.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.errors import InvalidProjectionSchemaError
from dashboard_app.publication.generator import (
    RawArtifactInput,
    UnknownArtifactRoleError,
    build_projection_bundle,
)
from dashboard_app.publication.manifest import (
    PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
    PortfolioStudyManifest,
    StudyMaturity,
)
from dashboard_app.publication.projection import (
    PUBLIC_PROJECTION_SCHEMA_VERSION,
    ProjectedArtifact,
    PublicProjectionBundle,
)
from dashboard_app.publication.sanitizers import (
    sanitize_predictive_run_metrics,
    sanitize_predictive_threshold_sensitivity,
    sanitize_promoted_artifact_identity,
    sanitize_strategy_research_run_summary,
    sanitize_verdict_report,
)
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    StudyEvidence,
    load_projection_bundle,
    load_projection_bundle_from_path,
    load_study_manifest,
    load_study_manifest_from_path,
    resolve_study_evidence,
)

_RAW_VERDICT_PAYLOAD = {
    "schema_version": "predictive_run_verdict.v1",
    "rule_set_version": "verdict_rules.v1",
    "rule_set": {"overfit_gap_ratio": 1.0},
    "run_id": "2ef6426b3cc06463",
    "dataset_id": "437f6b7f9240208f",
    "dataset_fingerprint": "437f6b7f9240208f93af9024a8e790cd1ff520a7c8c74de1d16500b72b3da156",
    "verdict": "INCONCLUSIVE",
    "facts": {"pooled_model_primary": 0.52},
    "rules": [
        {
            "rule_id": "O3",
            "fired": True,
            "observed": {"baseline_delta": 0.0169, "fold_win_rate": 0.5},
            "threshold": {"baseline_delta_gt": 0.0, "fold_win_rate_lt": 0.6667},
            "source": "pooled_model_primary, pooled_random_permutation_primary",
            "evaluated": True,
            "missing_input": None,
            "internal_debug_note": "should never survive sanitization",
        },
    ],
    "storage_path": (
        "/private/user_data/workspace/research/predictive_research/runs/2ef6426b3cc06463"
    ),
    "config": {"database_password": "hunter2"},
    "hostname": "internal-worker-03.local",
    "internal_notes": "plausible-looking but never allowlisted",
}

_RAW_PROMOTED_ARTIFACT_PAYLOAD = {
    "schema_version": "promoted_artifact.v1",
    "artifact_fingerprint": "a" * 64,
    "run_fingerprint": "b" * 64,
    "dataset_fingerprint": "c" * 64,
    "fold_id": 2,
    "features": ["feature-a", "feature-b"],
    "model_family": "sklearn.ridge",
    "preprocessing_spec": {"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
    "estimator_spec": {"alpha": 1.0},
    "training_library": "scikit-learn",
    "training_library_version": "1.4.0",
    "storage_path": "/private/user_data/workspace/research/predictive_research/promoted/aaaa",
    "hostname": "internal-worker-03.local",
}


_RAW_METRICS_PAYLOAD = {
    "schema_version": "predictive_metrics.v1",
    "run_id": "2ef6426b3cc06463",
    "dataset_id": "437f6b7f9240208f",
    "task_type": "CLASSIFICATION",
    "decision_threshold": 0.5,
    "seed": 42,
    "storage_path": (
        "/private/user_data/workspace/research/predictive_research/runs/2ef6426b3cc06463"
    ),
    "pooled": {
        "MODEL": {
            "statistical": {"roc_auc": 0.5239, "accuracy": 0.51, "log_loss": 0.69},
            "finance": {"mean_forward_return_selected": 0.001},
        },
        "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.5070}},
        "MAJORITY_CLASS": {"statistical": {"roc_auc": 0.5}},
    },
    "folds": {
        "0": {
            "MODEL": {"statistical": {"roc_auc": 0.5343}},
            "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.4880}},
        }
    },
    "fold_primary": {"0": {"train_primary": 0.5, "test_primary": 0.51}},
}

_RAW_THRESHOLD_SENSITIVITY_PAYLOAD = {
    "schema_version": "threshold_sensitivity.v1",
    "run_id": "2ef6426b3cc06463",
    "points": [
        {
            "threshold": 0.05,
            "statistical": {"accuracy": 0.5},
            "finance": {
                "coverage": 1.0,
                "hit_rate": 0.551,
                "mean_forward_return_selected": 0.002,
                "mean_forward_return_all": 0.001,
            },
        },
        {
            "threshold": 0.6,
            "statistical": {"accuracy": 0.6},
            "finance": {"coverage": 0.013, "hit_rate": 0.644},
        },
    ],
}

_RAW_STRATEGY_RUN_SUMMARY_PAYLOAD = {
    "schema_version": "strategy_summary_metrics.v1",
    "run_id": "8d050f623a034a58",
    "net_pnl": 1198499.9,
    "total_return": 11.98,
    "max_drawdown": -500.0,
    "sharpe_ratio": 1.2,
    "trade_count": 6200,
    "win_rate": 0.5135,
    "avg_win": 300.0,
    "avg_loss": -250.0,
}


def test_sanitize_verdict_report_retains_allowed_and_omits_forbidden() -> None:
    sanitized = sanitize_verdict_report(_RAW_VERDICT_PAYLOAD)

    assert set(sanitized) == {"verdict", "rule_set_version", "evaluations"}
    assert sanitized["verdict"] == "INCONCLUSIVE"
    assert sanitized["rule_set_version"] == "verdict_rules.v1"
    assert len(sanitized["evaluations"]) == 1
    evaluation = sanitized["evaluations"][0]
    assert set(evaluation) == {
        "rule_id",
        "fired",
        "observed",
        "threshold",
        "source",
        "evaluated",
        "missing_input",
    }
    assert evaluation["rule_id"] == "O3"
    assert "internal_debug_note" not in evaluation


def test_sanitize_promoted_artifact_identity_scalar_only() -> None:
    sanitized = sanitize_promoted_artifact_identity(_RAW_PROMOTED_ARTIFACT_PAYLOAD)

    assert sanitized == {"artifact_fingerprint": "a" * 64}


def test_sanitize_predictive_run_metrics_retains_allowed_and_omits_forbidden() -> None:
    sanitized = sanitize_predictive_run_metrics(_RAW_METRICS_PAYLOAD)

    assert set(sanitized) == {"decision_threshold", "seed", "pooled", "folds"}
    assert sanitized["decision_threshold"] == 0.5
    assert sanitized["seed"] == 42
    # MAJORITY_CLASS is a real pooled key but no accepted chart reads it --
    # must not survive even though it is a real, not a forbidden, field.
    assert set(sanitized["pooled"]) == {"MODEL", "RANDOM_PERMUTATION"}
    assert sanitized["pooled"]["MODEL"] == {"statistical": {"roc_auc": 0.5239}}
    assert sanitized["pooled"]["RANDOM_PERMUTATION"] == {"statistical": {"roc_auc": 0.5070}}
    assert set(sanitized["folds"]) == {"0"}
    assert sanitized["folds"]["0"] == {
        "MODEL": {"statistical": {"roc_auc": 0.5343}},
        "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.4880}},
    }
    for forbidden in ("run_id", "dataset_id", "task_type", "storage_path", "fold_primary"):
        assert forbidden not in sanitized


def test_sanitize_predictive_threshold_sensitivity_retains_allowed_and_omits_forbidden() -> None:
    sanitized = sanitize_predictive_threshold_sensitivity(_RAW_THRESHOLD_SENSITIVITY_PAYLOAD)

    assert set(sanitized) == {"points"}
    assert len(sanitized["points"]) == 2
    first = sanitized["points"][0]
    assert set(first) == {"threshold", "finance"}
    assert first["threshold"] == 0.05
    assert set(first["finance"]) == {"coverage", "hit_rate"}
    assert first["finance"]["coverage"] == 1.0
    assert first["finance"]["hit_rate"] == 0.551
    assert "statistical" not in first
    assert "mean_forward_return_selected" not in first["finance"]
    assert "mean_forward_return_all" not in first["finance"]
    for point in sanitized["points"]:
        assert "run_id" not in point


def test_sanitize_strategy_research_run_summary_retains_allowed_and_omits_forbidden() -> None:
    sanitized = sanitize_strategy_research_run_summary(_RAW_STRATEGY_RUN_SUMMARY_PAYLOAD)

    assert sanitized == {
        "run_id": "8d050f623a034a58",
        "net_pnl": 1198499.9,
        "trade_count": 6200,
        "win_rate": 0.5135,
    }
    for forbidden in ("total_return", "max_drawdown", "sharpe_ratio", "avg_win", "avg_loss"):
        assert forbidden not in sanitized


def test_generator_builds_bundle_with_correct_schema_version() -> None:
    bundle = build_projection_bundle(
        [
            RawArtifactInput(
                artifact_id="verdict-1",
                artifact_role="predictive_run_verdict",
                raw_payload=_RAW_VERDICT_PAYLOAD,
            ),
            RawArtifactInput(
                artifact_id="promotion-1",
                artifact_role="promoted_artifact_identity",
                raw_payload=_RAW_PROMOTED_ARTIFACT_PAYLOAD,
            ),
        ],
        generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
    )

    assert bundle.schema_version == PUBLIC_PROJECTION_SCHEMA_VERSION
    assert set(bundle.artifacts) == {"verdict-1", "promotion-1"}
    for artifact in bundle.artifacts.values():
        assert "storage_path" not in artifact.fields
        for value in artifact.fields.values():
            assert "/private/" not in repr(value)


def test_generator_raises_for_unknown_artifact_role() -> None:
    with pytest.raises(UnknownArtifactRoleError):
        build_projection_bundle(
            [
                RawArtifactInput(
                    artifact_id="x", artifact_role="not_a_registered_role", raw_payload={}
                )
            ],
            generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
        )


def test_projection_bundle_round_trip_to_dict_from_dict() -> None:
    bundle = PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version="dashboard.publication.generator.v1",
        generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
        artifacts={
            "verdict-1": ProjectedArtifact(
                artifact_id="verdict-1",
                artifact_role="predictive_run_verdict",
                fields={"verdict": "INCONCLUSIVE", "rule_set_version": "verdict_rules.v1"},
            )
        },
    )

    round_tripped = PublicProjectionBundle.from_dict(bundle.to_dict())

    assert round_tripped == bundle


def test_projection_bundle_rejects_major_schema_mismatch() -> None:
    payload = {
        "schema_version": "dashboard.public.v2",
        "generator_version": "dashboard.publication.generator.v1",
        "generated_at_utc": "2026-09-09T00:00:00+00:00",
        "artifacts": {},
    }

    with pytest.raises(InvalidProjectionSchemaError):
        PublicProjectionBundle.from_dict(payload)


def test_projection_bundle_rejects_malformed_artifact_entry() -> None:
    """A corrupted per-artifact entry must fail closed, not raise KeyError."""
    payload = {
        "schema_version": PUBLIC_PROJECTION_SCHEMA_VERSION,
        "generator_version": "dashboard.publication.generator.v1",
        "generated_at_utc": "2026-09-09T00:00:00+00:00",
        "artifacts": {"bad-1": {"artifact_role": "predictive_run_verdict", "fields": {}}},
    }

    with pytest.raises(InvalidProjectionSchemaError):
        PublicProjectionBundle.from_dict(payload)


def test_study_manifest_round_trip() -> None:
    manifest = PortfolioStudyManifest(
        schema_version=PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
        slug="btc-signal-quality",
        title="BTC Signal Quality",
        maturity=StudyMaturity.AS_BUILT,
        workflows=(WorkflowKind.SIGNAL, WorkflowKind.PREDICTIVE),
        artifact_roles={"verdict": "verdict-1", "promotion": "promotion-1"},
    )

    round_tripped = PortfolioStudyManifest.from_dict(manifest.to_dict())

    assert round_tripped == manifest


def test_resolve_study_evidence_dangling_reference_fails_closed() -> None:
    manifest = PortfolioStudyManifest(
        schema_version=PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
        slug="btc-signal-quality",
        title="BTC Signal Quality",
        maturity=StudyMaturity.AS_BUILT,
        workflows=(WorkflowKind.PREDICTIVE,),
        artifact_roles={"missing_role": "artifact-does-not-exist"},
    )
    bundle = PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version="dashboard.publication.generator.v1",
        generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
        artifacts={},
    )

    result = resolve_study_evidence(manifest, bundle)

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "dangling_reference"


def test_resolve_study_evidence_success() -> None:
    artifact = ProjectedArtifact(
        artifact_id="verdict-1",
        artifact_role="predictive_run_verdict",
        fields={"verdict": "INCONCLUSIVE"},
    )
    manifest = PortfolioStudyManifest(
        schema_version=PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
        slug="btc-signal-quality",
        title="BTC Signal Quality",
        maturity=StudyMaturity.AS_BUILT,
        workflows=(WorkflowKind.PREDICTIVE,),
        artifact_roles={"verdict": "verdict-1"},
    )
    bundle = PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version="dashboard.publication.generator.v1",
        generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
        artifacts={"verdict-1": artifact},
    )

    result = resolve_study_evidence(manifest, bundle)

    assert isinstance(result, StudyEvidence)
    assert result.resolved_artifacts == {"verdict": artifact}


def test_load_projection_bundle_missing_returns_unavailable() -> None:
    result = load_projection_bundle(None)

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "bundle_missing"


def test_load_projection_bundle_invalid_schema_returns_unavailable() -> None:
    result = load_projection_bundle({"schema_version": "dashboard.public.v0"})

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "schema_mismatch"


def test_load_projection_bundle_from_path_missing_file_returns_unavailable(
    tmp_path: Path,
) -> None:
    result = load_projection_bundle_from_path(tmp_path / "does-not-exist.json")

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "bundle_missing"


def test_load_projection_bundle_from_path_round_trips_a_real_file(tmp_path: Path) -> None:
    bundle = PublicProjectionBundle(
        schema_version=PUBLIC_PROJECTION_SCHEMA_VERSION,
        generator_version="dashboard.publication.generator.v1",
        generated_at_utc=datetime(2026, 9, 9, tzinfo=UTC),
        artifacts={
            "verdict-1": ProjectedArtifact(
                artifact_id="verdict-1",
                artifact_role="predictive_run_verdict",
                fields={"verdict": "INCONCLUSIVE"},
            )
        },
    )
    path = tmp_path / "projection.json"
    path.write_text(json.dumps(bundle.to_dict()), encoding="utf-8")

    result = load_projection_bundle_from_path(path)

    assert result == bundle


def test_load_study_manifest_missing_returns_unavailable() -> None:
    result = load_study_manifest(None)

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "manifest_missing"


def test_load_study_manifest_invalid_maturity_returns_unavailable() -> None:
    result = load_study_manifest(
        {
            "schema_version": PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
            "slug": "btc-signal-quality",
            "title": "BTC Signal Quality",
            "maturity": "NOT_A_REAL_MATURITY",
            "workflows": [],
            "artifact_roles": {},
        }
    )

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "schema_mismatch"


def test_load_study_manifest_from_path_missing_file_returns_unavailable(tmp_path: Path) -> None:
    result = load_study_manifest_from_path(tmp_path / "does-not-exist.json")

    assert isinstance(result, PublicationUnavailable)
    assert result.reason == "manifest_missing"


def test_load_study_manifest_from_path_round_trips_a_real_file(tmp_path: Path) -> None:
    manifest = PortfolioStudyManifest(
        schema_version=PORTFOLIO_STUDY_MANIFEST_SCHEMA_VERSION,
        slug="btc-signal-quality",
        title="BTC Signal Quality",
        maturity=StudyMaturity.AS_BUILT,
        workflows=(WorkflowKind.SIGNAL, WorkflowKind.PREDICTIVE),
        artifact_roles={"verdict": "verdict-1"},
    )
    path = tmp_path / "btc-signal-quality.json"
    path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")

    result = load_study_manifest_from_path(path)

    assert result == manifest
