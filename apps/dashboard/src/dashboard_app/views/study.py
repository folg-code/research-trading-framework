"""BTC Signal Quality study view (Sprint 060 T003).

The first real consumer of the ADR-0034 publication boundary: loads the
committed public projection bundle and the hand-authored study manifest,
resolves them, and renders the study content, the persisted verdict
verbatim, and the three accepted charts (D060-01). Every load/resolve step
fails closed -- ``PublicationUnavailable`` renders an explicit warning,
never a crash and never a dashboard-computed fallback (D060-03; ADR-0034
S1.6, S2.4).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from dashboard_app.charts.builders import (
    build_signal_quality_fold_roc_auc_figure,
    build_signal_quality_threshold_coverage_figure,
    build_signal_quality_trade_disposition_figure,
)
from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.contracts import (
    SignalQualityFoldRocAucRow,
    SignalQualityThresholdPoint,
    SignalQualityTradeDispositionRow,
)
from dashboard_app.publication.paths import projection_bundle_path, study_manifest_path
from dashboard_app.publication.projection import ProjectedArtifact
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    StudyEvidence,
    load_projection_bundle_from_path,
    load_study_manifest_from_path,
    resolve_study_evidence,
)

#: The one study this view renders. A second study would be a new manifest
#: file and a new content document, not a change to this constant's shape.
STUDY_SLUG = "btc-signal-quality"
STUDY_CONTENT_SLUG = "btc-signal-quality-study"


def load_btc_signal_quality_evidence() -> StudyEvidence | PublicationUnavailable:
    """Resolve the BTC Signal Quality study's manifest against the committed bundle."""
    manifest = load_study_manifest_from_path(study_manifest_path(STUDY_SLUG))
    if isinstance(manifest, PublicationUnavailable):
        return manifest

    bundle = load_projection_bundle_from_path(projection_bundle_path())
    if isinstance(bundle, PublicationUnavailable):
        return bundle

    return resolve_study_evidence(manifest, bundle)


def _metric_source_roc_auc(source_group: Mapping[str, Any], source: str) -> float | None:
    payload = source_group.get(source, {})
    if not isinstance(payload, Mapping):
        return None
    statistical = payload.get("statistical", {})
    if not isinstance(statistical, Mapping):
        return None
    value = statistical.get("roc_auc")
    return float(value) if isinstance(value, int | float) else None


def _fold_roc_auc_row(label: str, source_group: Mapping[str, Any]) -> SignalQualityFoldRocAucRow:
    return SignalQualityFoldRocAucRow(
        fold_id=label,
        model_roc_auc=_metric_source_roc_auc(source_group, "MODEL"),
        random_permutation_roc_auc=_metric_source_roc_auc(source_group, "RANDOM_PERMUTATION"),
    )


def build_fold_roc_auc_rows(
    metrics_fields: Mapping[str, Any],
) -> tuple[SignalQualityFoldRocAucRow | None, tuple[SignalQualityFoldRocAucRow, ...]]:
    """Build the pooled and ordered per-fold rows from a sanitized
    ``predictive_run_metrics`` payload."""
    pooled_raw = metrics_fields.get("pooled")
    pooled = _fold_roc_auc_row("Pooled", pooled_raw) if isinstance(pooled_raw, Mapping) else None

    folds_raw = metrics_fields.get("folds", {})
    fold_rows: tuple[SignalQualityFoldRocAucRow, ...] = ()
    if isinstance(folds_raw, Mapping):
        fold_rows = tuple(
            _fold_roc_auc_row(f"Fold {fold_id}", fold_payload)
            for fold_id, fold_payload in sorted(folds_raw.items())
            if isinstance(fold_payload, Mapping)
        )
    return pooled, fold_rows


def build_threshold_points(
    threshold_sensitivity_fields: Mapping[str, Any],
) -> tuple[SignalQualityThresholdPoint, ...]:
    """Build ordered threshold points from a sanitized
    ``predictive_threshold_sensitivity`` payload."""
    raw_points = threshold_sensitivity_fields.get("points", [])
    if not isinstance(raw_points, list):
        return ()

    points = []
    for entry in raw_points:
        if not isinstance(entry, Mapping) or "threshold" not in entry:
            continue
        finance = entry.get("finance", {})
        coverage = finance.get("coverage") if isinstance(finance, Mapping) else None
        hit_rate = finance.get("hit_rate") if isinstance(finance, Mapping) else None
        points.append(
            SignalQualityThresholdPoint(
                threshold=float(entry["threshold"]),
                coverage=float(coverage) if isinstance(coverage, int | float) else None,
                hit_rate=float(hit_rate) if isinstance(hit_rate, int | float) else None,
            )
        )
    return tuple(points)


def build_trade_disposition_rows(
    baseline: ProjectedArtifact, scored: ProjectedArtifact
) -> tuple[SignalQualityTradeDispositionRow, ...]:
    """Build the baseline/scored rows from two sanitized
    ``strategy_research_run_summary`` payloads."""

    def _row(label: str, artifact: ProjectedArtifact) -> SignalQualityTradeDispositionRow:
        fields = artifact.fields
        net_pnl = fields.get("net_pnl")
        trade_count = fields.get("trade_count")
        win_rate = fields.get("win_rate")
        return SignalQualityTradeDispositionRow(
            label=label,
            trade_count=int(trade_count) if isinstance(trade_count, int) else None,
            win_rate=float(win_rate) if isinstance(win_rate, int | float) else None,
            net_pnl=float(net_pnl) if net_pnl is not None else None,
        )

    return (_row("Baseline", baseline), _row("Scored", scored))


def render_btc_signal_quality_study() -> None:
    """Render the BTC Signal Quality study page: content, verdict, three charts."""
    st.title("BTC Signal Quality Study")

    evidence = load_btc_signal_quality_evidence()
    if isinstance(evidence, PublicationUnavailable):
        st.warning(f"Study evidence unavailable ({evidence.reason}): {evidence.detail}")
        return

    content = load_content_document(content_document_path(STUDY_CONTENT_SLUG))
    if isinstance(content, ContentUnavailable):
        st.warning(f"Study content unavailable ({content.reason}): {content.detail}")
    else:
        st.markdown(content.body_markdown)

    verdict_artifact = evidence.resolved_artifacts.get("verdict")
    if verdict_artifact is not None:
        st.subheader("Persisted verdict")
        st.badge(str(verdict_artifact.fields.get("verdict", "UNKNOWN")), color="gray")

    metrics_artifact = evidence.resolved_artifacts.get("predictive_metrics")
    if metrics_artifact is not None:
        st.subheader("Model vs. random-permutation ROC AUC")
        st.caption(
            "Pooled and per-fold ROC AUC for the trained model against a "
            "random-permutation baseline. Decision threshold and seed are "
            "the run's declared assumptions, fixed before results were seen."
        )
        pooled, folds = build_fold_roc_auc_rows(metrics_artifact.fields)
        st.plotly_chart(
            build_signal_quality_fold_roc_auc_figure(pooled, folds), use_container_width=True
        )
        decision_threshold = metrics_artifact.fields.get("decision_threshold")
        seed = metrics_artifact.fields.get("seed")
        if decision_threshold is not None or seed is not None:
            st.caption(f"Decision threshold: {decision_threshold}. Seed: {seed}.")

    threshold_artifact = evidence.resolved_artifacts.get("threshold_sensitivity")
    if threshold_artifact is not None:
        st.subheader("Threshold sensitivity")
        st.caption(
            "Coverage is the share of occurrences a threshold still selects; "
            "hit rate is the share of selected occurrences that resolved "
            "favorably. A usable threshold needs both to hold up together."
        )
        points = build_threshold_points(threshold_artifact.fields)
        st.plotly_chart(
            build_signal_quality_threshold_coverage_figure(points), use_container_width=True
        )

    baseline_artifact = evidence.resolved_artifacts.get("strategy_baseline")
    scored_artifact = evidence.resolved_artifacts.get("strategy_scored")
    if baseline_artifact is not None and scored_artifact is not None:
        st.subheader("Baseline vs. scored trade disposition")
        st.caption(
            "The same strategy simulated twice on the same data: once "
            "unscored, once filtered by the classifier at its declared "
            "threshold. Neither run is recomputed here -- both are "
            "persisted Strategy Research results."
        )
        rows = build_trade_disposition_rows(baseline_artifact, scored_artifact)
        st.plotly_chart(
            build_signal_quality_trade_disposition_figure(rows), use_container_width=True
        )
