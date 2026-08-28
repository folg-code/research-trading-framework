"""Predictive Research page — study picker, leaderboard, run detail (S044-T004-T010).

Read-only (D-S044-09): no training, no estimator import, no blob deserialize.
Every number shown here comes from a persisted ``manifest.json`` / ``metrics.json``
sidecar, never a value recomputed in the UI.
"""

from __future__ import annotations

import streamlit as st

from dashboard_app.caching.streamlit import cached_list_predictive_catalog, storage_fingerprint
from dashboard_app.charts import (
    build_predictive_bucket_figure,
    build_predictive_calibration_figure,
    build_predictive_fold_stability_figure,
    build_predictive_importance_figure,
    build_predictive_learning_curve_figure,
)
from dashboard_app.contracts import PredictiveDatasetSummary
from dashboard_app.formatting import format_created_at
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.predictive import (
    build_importance_view,
    build_leaderboard_rows,
    build_learning_curves_view,
    build_run_metrics_view,
    build_window_accounting_rows,
    load_run_importance,
    load_run_learning_curves,
    load_run_metrics,
    load_run_provenance,
    load_run_window_accounting,
    report_html_path,
    runs_for_dataset,
)

configure_page(title="Predictive Research")
settings = render_app_chrome()

st.title("Predictive Research")
st.caption(
    "Browse persisted predictive-study datasets and runs. Read-only: numbers come from "
    "`metrics.json` and its sidecars, never recomputed here."
)

if settings is None:
    st.warning("Storage is not configured. Set `DASHBOARD_STORAGE_ROOT` or use System diagnostics.")
    st.stop()

fingerprint = storage_fingerprint(settings.storage_root)
catalog = cached_list_predictive_catalog(str(settings.storage_root), fingerprint.token)

if not catalog.datasets:
    st.info("No predictive studies found under this storage root.")
    if catalog.issues:
        with st.expander(f"Catalog issues ({len(catalog.issues)})"):
            for issue in catalog.issues:
                st.write(f"`{issue.path}` — {issue.reason}")
    st.stop()


# --- Study picker (T004) -----------------------------------------------------------
def _dataset_label(dataset: PredictiveDatasetSummary) -> str:
    ref = dataset.source_dataset_ref or dataset.dataset_id
    return (
        f"{format_created_at(dataset.created_at_utc)} · {ref} "
        f"· {dataset.label_kind or '—'} / {dataset.horizon or '—'} "
        f"· {dataset.run_count} run(s)"
    )


dataset_options = {_dataset_label(dataset): dataset for dataset in catalog.datasets}
selected_label = st.selectbox(
    "Study", options=list(dataset_options), key="predictive_dataset_picker"
)
dataset = dataset_options[selected_label]

with st.expander("Study identity", expanded=False):
    st.write(
        {
            "dataset_id": dataset.dataset_id,
            "dataset_fingerprint": dataset.dataset_fingerprint,
            "source_dataset_ref": dataset.source_dataset_ref,
            "label_kind": dataset.label_kind,
            "horizon": dataset.horizon,
            "run_count": dataset.run_count,
            "storage_path": dataset.storage_path,
        }
    )

# --- Leaderboard (T005) ------------------------------------------------------------
st.subheader("Leaderboard")
st.caption(
    "Sorted by baseline delta (MODEL minus RANDOM_PERMUTATION), not the raw metric — "
    "a run that barely beats a weak permutation baseline still outranks a stronger "
    "raw score against a tougher baseline."
)
dataset_runs = runs_for_dataset(catalog.runs, dataset.dataset_fingerprint)
if not dataset_runs:
    st.info("No runs for this study yet.")
    st.stop()

rows = build_leaderboard_rows(dataset_runs)
st.dataframe(
    [
        {
            "run_id": row.run_id,
            "created": row.created_at,
            "family": row.family,
            "metric": row.primary_metric_label,
            "value": row.primary_metric_display,
            "baseline delta": row.baseline_delta_display,
            "flags": ", ".join(row.quality_flag_codes)
            or ("missing baseline" if row.missing_baseline else "—"),
        }
        for row in rows
    ],
    use_container_width=True,
    hide_index=True,
)

# --- Run detail (T006) --------------------------------------------------------------
st.subheader("Run detail")
run_options = {f"{row.run_id} ({row.family})": row.run_id for row in rows}
selected_run_label = st.selectbox("Run", options=list(run_options), key="predictive_run_picker")
selected_run_id = run_options[selected_run_label]
selected_run = next(run for run in dataset_runs if run.run_id == selected_run_id)

if not selected_run.has_metrics:
    st.warning("This run has no `metrics.json` sidecar; only identity is shown.")

metrics_payload = load_run_metrics(selected_run.storage_path)
metrics_view = build_run_metrics_view(metrics_payload)

if metrics_view is None:
    st.info("No metrics available for this run.")
else:
    cols = st.columns(3)
    cols[0].metric(
        f"Pooled {metrics_view.primary_metric_name or 'metric'} (MODEL)",
        f"{metrics_view.pooled_model_value:.3f}"
        if metrics_view.pooled_model_value is not None
        else "—",
    )
    cols[1].metric(
        "Pooled RANDOM_PERMUTATION",
        f"{metrics_view.pooled_permutation_value:.3f}"
        if metrics_view.pooled_permutation_value is not None
        else "—",
    )
    cols[2].metric(
        "Baseline delta",
        f"{metrics_view.baseline_delta:+.3f}"
        if metrics_view.baseline_delta is not None
        else "no baseline",
    )

    st.caption(
        "Per-fold metrics (AC3: never shown as a pooled figure alone — see the table below)."
    )
    if metrics_view.fold_rows:
        st.plotly_chart(
            build_predictive_fold_stability_figure(metrics_view.fold_rows), use_container_width=True
        )
        st.dataframe(
            [
                {
                    "fold": row.fold_id,
                    "MODEL": row.model_value,
                    "RANDOM_PERMUTATION": row.permutation_value,
                    "train": row.train_primary,
                    "test": row.test_primary,
                    "train - test gap": row.primary_gap,
                }
                for row in metrics_view.fold_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No per-fold metrics persisted for this run.")

    if metrics_view.bucket_rows:
        st.caption("Prediction buckets (pooled MODEL, TEST rows).")
        st.plotly_chart(
            build_predictive_bucket_figure(metrics_view.bucket_rows), use_container_width=True
        )
        bucket_cols = st.columns(2)
        bucket_cols[0].metric(
            "Top - bottom spread",
            f"{metrics_view.top_bottom_spread:.4f}"
            if metrics_view.top_bottom_spread is not None
            else "—",
        )
        bucket_cols[1].metric(
            "Hit rate", f"{metrics_view.hit_rate:.1%}" if metrics_view.hit_rate is not None else "—"
        )

    if metrics_view.calibration_bins:
        st.caption("Calibration (classification runs with persisted probabilities only).")
        st.plotly_chart(
            build_predictive_calibration_figure(metrics_view.calibration_bins),
            use_container_width=True,
        )

# --- Importance panel (T007) --------------------------------------------------------
st.subheader("Feature importance")
importance_payload = load_run_importance(selected_run.storage_path)
importance_rows = build_importance_view(importance_payload)
if importance_rows:
    st.caption("Out-of-sample permutation importance, averaged across folds.")
    st.plotly_chart(build_predictive_importance_figure(importance_rows), use_container_width=True)
else:
    st.info("No `importance.json` sidecar for this run.")

with st.expander("Learning curves (neural families only)", expanded=False):
    learning_curves = build_learning_curves_view(
        load_run_learning_curves(selected_run.storage_path)
    )
    if learning_curves:
        for curve in learning_curves:
            st.plotly_chart(build_predictive_learning_curve_figure(curve), use_container_width=True)
    else:
        st.info("No `learning_curves.json` sidecar for this run.")

with st.expander("Window accounting (sequence families only)", expanded=False):
    window_rows = build_window_accounting_rows(
        load_run_window_accounting(selected_run.storage_path)
    )
    if window_rows:
        st.dataframe(
            [
                {
                    "fold": row.fold_id,
                    "role": row.fold_role,
                    "candidate rows": row.candidate_end_rows,
                    "windows built": row.windows_built,
                    "dropped (incomplete)": row.windows_dropped_incomplete,
                    "dropped (gap)": row.windows_dropped_gap,
                    "dropped (fold boundary)": row.windows_dropped_fold_boundary,
                }
                for row in window_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No `window_accounting.json` sidecar for this run.")

# --- Provenance + report link (T008) -------------------------------------------------
st.subheader("Provenance")
provenance = load_run_provenance(settings.storage_root, selected_run.run_id)
if provenance is None:
    st.info("No provenance manifest for this run.")
else:
    st.write(
        {
            "dataset_fingerprint": provenance.dataset_fingerprint,
            "run_fingerprint": provenance.run_fingerprint,
            "estimator_family": provenance.estimator_family,
            "task_type": provenance.task_type,
            "seed": provenance.estimator_seed,
            "preprocessing_spec": provenance.preprocessing_spec,
            "library": provenance.library,
            "library_version": provenance.library_version,
            "framework_version": provenance.framework_version,
        }
    )

report_path = report_html_path(selected_run.storage_path)
if report_path is not None:
    st.link_button("Open offline report.html", f"file://{report_path}")
    st.caption(f"`{report_path}`")
else:
    st.caption("No `report.html` for this run.")

if catalog.issues:
    with st.expander(f"Catalog issues ({len(catalog.issues)})"):
        for issue in catalog.issues:
            st.write(f"`{issue.path}` — {issue.reason}")
