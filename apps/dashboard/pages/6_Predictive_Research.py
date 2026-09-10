"""Predictive Research — one representative projected evidence view."""

from __future__ import annotations

import streamlit as st

from dashboard_app.charts.builders import build_signal_quality_fold_roc_auc_figure
from dashboard_app.publication.catalog_index import load_public_catalog_from_paths
from dashboard_app.publication.paths import STUDY_MANIFESTS_ROOT, projection_bundle_path
from dashboard_app.publication.validation import PublicationUnavailable
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.public_catalog import build_public_catalog_row
from dashboard_app.views.study import build_fold_roc_auc_rows, load_btc_signal_quality_evidence

configure_page(title="Predictive Research")
render_app_chrome()

st.title("Predictive Research Evidence")
st.caption(
    "One representative persisted out-of-sample evaluation. The workflow supports linear, "
    "tree and neural families; this page deliberately shows one allowlisted run rather than "
    "a private-workspace leaderboard."
)

catalog = load_public_catalog_from_paths(projection_bundle_path(), STUDY_MANIFESTS_ROOT)
evidence = load_btc_signal_quality_evidence()
if isinstance(catalog, PublicationUnavailable) or isinstance(evidence, PublicationUnavailable):
    st.warning("Published Predictive Research evidence is unavailable for this release.")
    st.stop()

catalog_artifact = evidence.resolved_artifacts.get("catalog_predictive")
representative = (
    next(
        (run for run in catalog.runs if run.artifact_id == catalog_artifact.artifact_id),
        None,
    )
    if catalog_artifact is not None
    else None
)
if representative is None:
    st.warning("The study manifest does not name a projected representative Predictive run.")
    st.stop()

row = build_public_catalog_row(representative)
st.write(
    {
        "run": row.run_id,
        "model": row.model,
        "dataset": row.dataset,
        "timeframe": row.timeframe,
        "research time range": row.time_range,
        "persisted verdict": row.verdict,
    }
)

metrics = evidence.resolved_artifacts.get("predictive_metrics")
st.subheader("Model vs random-permutation ROC AUC")
if metrics is None:
    st.info("No allowlisted fold metrics are published for the representative run.")
else:
    pooled, folds = build_fold_roc_auc_rows(metrics.fields)
    st.plotly_chart(
        build_signal_quality_fold_roc_auc_figure(pooled, folds),
        use_container_width=True,
    )
    st.caption(
        f"Decision threshold: {metrics.fields.get('decision_threshold', '—')}. "
        f"Seed: {metrics.fields.get('seed', '—')}. Values are copied from persisted evidence."
    )

verdict = evidence.resolved_artifacts.get("verdict")
st.subheader("Persisted analyst verdict")
if verdict is None:
    st.info("NO VERDICT")
else:
    st.badge(str(verdict.fields.get("verdict", "NO VERDICT")), color="gray")
    st.caption(f"Rule set: {verdict.fields.get('rule_set_version', '—')}.")

st.caption(
    "The dashboard does not load model binaries, recompute metrics, rank model families or "
    "derive a verdict. Additional predictive runs remain discoverable in Research Catalog."
)
