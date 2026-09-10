"""Tests for the BTC Signal Quality study's data-building helpers (Sprint 060 T003).

``render_btc_signal_quality_study`` itself (the ``st.*``-calling function) is
covered by ``test_study_acceptance.py``'s ``AppTest``-based render, matching
``test_overview_acceptance.py``'s convention -- these tests exercise the
pure data-building functions directly.
"""

from __future__ import annotations

from dashboard_app.publication.projection import ProjectedArtifact
from dashboard_app.publication.validation import StudyEvidence
from dashboard_app.views.study import (
    build_fold_roc_auc_rows,
    build_threshold_points,
    build_trade_disposition_rows,
    load_btc_signal_quality_evidence,
)


def test_load_btc_signal_quality_evidence_resolves_the_real_committed_bundle() -> None:
    """The generator script's committed output must actually resolve end to end."""
    evidence = load_btc_signal_quality_evidence()

    assert isinstance(evidence, StudyEvidence)
    assert set(evidence.resolved_artifacts) == {
        "verdict",
        "predictive_metrics",
        "threshold_sensitivity",
        "promoted_artifact",
        "strategy_baseline",
        "strategy_scored",
    }
    assert evidence.resolved_artifacts["verdict"].fields["verdict"] == "INCONCLUSIVE"


def test_build_fold_roc_auc_rows_builds_pooled_and_ordered_folds() -> None:
    metrics_fields = {
        "pooled": {
            "MODEL": {"statistical": {"roc_auc": 0.5239}},
            "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.5070}},
        },
        "folds": {
            "1": {
                "MODEL": {"statistical": {"roc_auc": 0.51}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.52}},
            },
            "0": {
                "MODEL": {"statistical": {"roc_auc": 0.53}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.49}},
            },
        },
    }

    pooled, folds = build_fold_roc_auc_rows(metrics_fields)

    assert pooled is not None
    assert pooled.model_roc_auc == 0.5239
    assert pooled.random_permutation_roc_auc == 0.5070
    assert [row.fold_id for row in folds] == ["Fold 0", "Fold 1"]
    assert folds[0].model_roc_auc == 0.53


def test_build_fold_roc_auc_rows_handles_missing_pooled() -> None:
    pooled, folds = build_fold_roc_auc_rows({})

    assert pooled is None
    assert folds == ()


def test_build_threshold_points_builds_sorted_by_input_order() -> None:
    threshold_fields = {
        "points": [
            {"threshold": 0.05, "finance": {"coverage": 1.0, "hit_rate": 0.55}},
            {"threshold": 0.6, "finance": {"coverage": 0.01, "hit_rate": 0.64}},
        ]
    }

    points = build_threshold_points(threshold_fields)

    assert len(points) == 2
    assert points[0].threshold == 0.05
    assert points[0].coverage == 1.0
    assert points[0].hit_rate == 0.55


def test_build_threshold_points_skips_entries_without_a_threshold() -> None:
    points = build_threshold_points({"points": [{"finance": {"coverage": 1.0}}]})

    assert points == ()


def test_build_threshold_points_handles_missing_points_key() -> None:
    assert build_threshold_points({}) == ()


def test_build_trade_disposition_rows_maps_baseline_and_scored() -> None:
    baseline = ProjectedArtifact(
        artifact_id="strategy-research-run-baseline",
        artifact_role="strategy_research_run_summary",
        fields={
            "run_id": "baseline-id",
            "trade_count": 6200,
            "win_rate": 0.5135,
            "net_pnl": 1198499.9,
        },
    )
    scored = ProjectedArtifact(
        artifact_id="strategy-research-run-scored",
        artifact_role="strategy_research_run_summary",
        fields={
            "run_id": "scored-id",
            "trade_count": 6198,
            "win_rate": 0.5136,
            "net_pnl": 1206906.6,
        },
    )

    rows = build_trade_disposition_rows(baseline, scored)

    assert [row.label for row in rows] == ["Baseline", "Scored"]
    assert rows[0].trade_count == 6200
    assert rows[1].net_pnl == 1206906.6


def test_build_trade_disposition_rows_handles_a_string_net_pnl() -> None:
    """polars' Decimal-typed net_pnl column round-trips through JSON as a string."""
    baseline = ProjectedArtifact(
        artifact_id="a",
        artifact_role="strategy_research_run_summary",
        fields={"net_pnl": "1198499.900000097"},
    )
    scored = ProjectedArtifact(
        artifact_id="b",
        artifact_role="strategy_research_run_summary",
        fields={"net_pnl": "1206906.6000000967"},
    )

    rows = build_trade_disposition_rows(baseline, scored)

    assert rows[0].net_pnl == 1198499.900000097
    assert rows[1].net_pnl == 1206906.6000000967
