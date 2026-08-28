"""Tests for the Predictive Research page view models (S044-T004-T010)."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_app.catalog import list_predictive_catalog
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
    sort_leaderboard,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _dataset_manifest(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "predictive_dataset.v1",
        "dataset_id": "d1",
        "dataset_fingerprint": "fp-d1",
        "study_spec": {"label": {"kind": "TRIPLE_BARRIER", "horizon": "20b"}},
        "source_dataset_ref": "NQ@continuous",
        "fold_summary": {
            "fold_count": 2,
            "role_counts": {"TRAIN": 600, "TEST": 200},
            "per_fold": [
                {"fold_id": 0, "TRAIN": 300, "TEST": 100},
                {"fold_id": 1, "TRAIN": 300, "TEST": 100},
            ],
        },
        "framework_version": "0.1",
        "created_at_utc": "2024-06-01T10:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def _run_manifest(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "predictive_run.v1",
        "run_id": "r1",
        "run_fingerprint": "fp-r1",
        "dataset_id": "d1",
        "dataset_fingerprint": "fp-d1",
        "estimator_spec": {
            "family": "logistic_regression",
            "seed": 42,
            "task_type": "CLASSIFICATION",
        },
        "preprocessing_spec": {"scaler": "standard"},
        "library": "sklearn",
        "library_version": "1.4.0",
        "framework_version": "0.1",
        "created_at_utc": "2024-06-02T10:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def _metrics(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "predictive_metrics.v1",
        "run_id": "r1",
        "task_type": "CLASSIFICATION",
        "folds": {
            "0": {
                "MODEL": {
                    "statistical": {"roc_auc": 0.60},
                    "finance": {
                        "mean_forward_return_by_decile": [0.0] * 10,
                        "top_bottom_spread": 0.01,
                        "hit_rate": 0.55,
                        "coverage": 1.0,
                        "mean_forward_return_selected": 0.01,
                        "mean_forward_return_all": 0.0,
                    },
                },
                "RANDOM_PERMUTATION": {
                    "statistical": {"roc_auc": 0.50},
                    "finance": {
                        "mean_forward_return_by_decile": [0.0] * 10,
                        "top_bottom_spread": 0.0,
                        "hit_rate": 0.5,
                        "coverage": 1.0,
                        "mean_forward_return_selected": 0.0,
                        "mean_forward_return_all": 0.0,
                    },
                },
            },
            "1": {
                "MODEL": {
                    "statistical": {"roc_auc": 0.62},
                    "finance": {
                        "mean_forward_return_by_decile": [0.0] * 10,
                        "top_bottom_spread": 0.01,
                        "hit_rate": 0.56,
                        "coverage": 1.0,
                        "mean_forward_return_selected": 0.01,
                        "mean_forward_return_all": 0.0,
                    },
                },
                "RANDOM_PERMUTATION": {
                    "statistical": {"roc_auc": 0.51},
                    "finance": {
                        "mean_forward_return_by_decile": [0.0] * 10,
                        "top_bottom_spread": 0.0,
                        "hit_rate": 0.5,
                        "coverage": 1.0,
                        "mean_forward_return_selected": 0.0,
                        "mean_forward_return_all": 0.0,
                    },
                },
            },
        },
        "pooled": {
            "MODEL": {
                "statistical": {
                    "roc_auc": 0.61,
                    "calibration_bins": [
                        {
                            "bin_index": 0,
                            "lower": 0.0,
                            "upper": 0.1,
                            "count": 10,
                            "mean_predicted": 0.05,
                            "mean_observed": 0.06,
                        },
                    ],
                },
                "finance": {
                    "mean_forward_return_by_decile": [0.01 * i for i in range(10)],
                    "top_bottom_spread": 0.09,
                    "hit_rate": 0.58,
                    "coverage": 1.0,
                    "mean_forward_return_selected": 0.05,
                    "mean_forward_return_all": 0.0,
                },
            },
            "RANDOM_PERMUTATION": {
                "statistical": {"roc_auc": 0.58},
                "finance": {
                    "mean_forward_return_by_decile": [0.0] * 10,
                    "top_bottom_spread": 0.0,
                    "hit_rate": 0.5,
                    "coverage": 1.0,
                    "mean_forward_return_selected": 0.0,
                    "mean_forward_return_all": 0.0,
                },
            },
        },
        "fold_primary": {
            "0": {"train_primary": 0.65, "test_primary": 0.60, "primary_gap": 0.05},
            "1": {"train_primary": 0.66, "test_primary": 0.62, "primary_gap": 0.04},
        },
    }
    payload.update(overrides)
    return payload


def _write_dataset(root: Path, dataset_id: str = "d1", **overrides: object) -> None:
    _write(
        root / "research" / "predictive_research" / "datasets" / dataset_id / "manifest.json",
        _dataset_manifest(dataset_id=dataset_id, **overrides),
    )


def _write_run(
    root: Path,
    run_id: str = "r1",
    *,
    metrics: dict[str, object] | None = None,
    manifest_overrides: dict[str, object] | None = None,
) -> Path:
    run_dir = root / "research" / "predictive_research" / "runs" / run_id
    _write(run_dir / "manifest.json", _run_manifest(run_id=run_id, **(manifest_overrides or {})))
    if metrics is not None:
        _write(run_dir / "metrics.json", metrics)
    return run_dir


# --- Leaderboard sort (T005) --------------------------------------------------------


def test_sort_leaderboard_ranks_by_baseline_delta_not_raw_metric(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    _write_run(
        tmp_path, run_id="strong-raw-weak-delta", metrics=_metrics()
    )  # 0.61 vs 0.58 -> +0.03
    _write_run(
        tmp_path,
        run_id="weak-raw-strong-delta",
        metrics=_metrics(
            pooled={
                "MODEL": {"statistical": {"roc_auc": 0.57}, "finance": _blank_finance()},
                "RANDOM_PERMUTATION": {
                    "statistical": {"roc_auc": 0.50},
                    "finance": _blank_finance(),
                },
            }
        ),
    )

    catalog = list_predictive_catalog(tmp_path)
    ordered = sort_leaderboard(catalog.runs)

    assert [run.run_id for run in ordered] == ["weak-raw-strong-delta", "strong-raw-weak-delta"]


def test_sort_leaderboard_puts_missing_baseline_last(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics_no_perm = _metrics()
    del metrics_no_perm["pooled"]["RANDOM_PERMUTATION"]  # type: ignore[index]
    _write_run(tmp_path, run_id="no-baseline", metrics=metrics_no_perm)
    _write_run(tmp_path, run_id="has-baseline", metrics=_metrics())

    catalog = list_predictive_catalog(tmp_path)
    ordered = sort_leaderboard(catalog.runs)

    assert ordered[-1].run_id == "no-baseline"
    assert ordered[0].run_id == "has-baseline"


def test_runs_for_dataset_filters_by_fingerprint(tmp_path: Path) -> None:
    _write_dataset(tmp_path, dataset_id="d1", dataset_fingerprint="fp-d1")
    _write_run(tmp_path, run_id="r1", metrics=_metrics())
    _write_run(
        tmp_path,
        run_id="r2",
        metrics=_metrics(run_id="r2"),
        manifest_overrides={"dataset_fingerprint": "fp-other", "dataset_id": "d2"},
    )

    catalog = list_predictive_catalog(tmp_path)
    filtered = runs_for_dataset(catalog.runs, "fp-d1")

    assert {run.run_id for run in filtered} == {"r1"}


def test_build_leaderboard_rows_flags_missing_baseline(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics_no_perm = _metrics()
    del metrics_no_perm["pooled"]["RANDOM_PERMUTATION"]  # type: ignore[index]
    _write_run(tmp_path, metrics=metrics_no_perm)

    catalog = list_predictive_catalog(tmp_path)
    rows = build_leaderboard_rows(catalog.runs)

    assert len(rows) == 1
    assert rows[0].missing_baseline is True
    assert rows[0].baseline_delta_display == "no baseline"


# --- Run detail (T006 / AC3) --------------------------------------------------------


def test_build_run_metrics_view_includes_per_fold_rows(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())

    payload = load_run_metrics(run_dir)
    view = build_run_metrics_view(payload)

    assert view is not None
    assert view.pooled_model_value == 0.61
    assert view.baseline_delta is not None
    assert round(view.baseline_delta, 2) == 0.03
    assert len(view.fold_rows) == 2
    assert view.fold_rows[0].fold_id == "0"
    assert view.fold_rows[0].model_value == 0.60
    assert view.fold_rows[0].permutation_value == 0.50
    assert view.fold_rows[0].primary_gap == 0.05


def test_build_run_metrics_view_includes_calibration_and_buckets(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    view = build_run_metrics_view(load_run_metrics(run_dir))

    assert view is not None
    assert len(view.calibration_bins) == 1
    assert view.calibration_bins[0].mean_predicted == 0.05
    assert len(view.bucket_rows) == 10
    assert view.top_bottom_spread == 0.09
    assert view.hit_rate == 0.58


def test_build_run_metrics_view_none_when_metrics_missing(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=None)
    assert load_run_metrics(run_dir) is None
    assert build_run_metrics_view(None) is None


# --- Importance panel (T007 / AC4) --------------------------------------------------


def test_build_importance_view_averages_across_folds(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    importance_payload = {
        "metric": "roc_auc",
        "n_repeats": 5,
        "folds": [
            {
                "fold_id": 0,
                "native": None,
                "permutation": {
                    "feature_names": ["f1", "f2"],
                    "importances_mean": [0.10, 0.02],
                    "importances_std": [0.01, 0.005],
                    "n_repeats": 5,
                    "seed": 42,
                    "metric": "roc_auc",
                },
                "train_primary": 0.65,
                "test_primary": 0.60,
                "primary_gap": 0.05,
            },
            {
                "fold_id": 1,
                "native": None,
                "permutation": {
                    "feature_names": ["f1", "f2"],
                    "importances_mean": [0.20, 0.04],
                    "importances_std": [0.02, 0.01],
                    "n_repeats": 5,
                    "seed": 42,
                    "metric": "roc_auc",
                },
                "train_primary": 0.66,
                "test_primary": 0.62,
                "primary_gap": 0.04,
            },
        ],
    }
    _write(run_dir / "importance.json", importance_payload)

    payload = load_run_importance(run_dir)
    rows = build_importance_view(payload)

    assert [row.feature_name for row in rows] == ["f1", "f2"]
    assert round(rows[0].mean_importance, 3) == 0.15
    assert round(rows[1].mean_importance, 3) == 0.03


def test_build_importance_view_degrades_when_missing(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    assert load_run_importance(run_dir) is None
    assert build_importance_view(None) == ()


# --- Learning curves / window accounting (T010 degrade-gracefully) ------------------


def test_build_learning_curves_view_degrades_when_missing(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    assert load_run_learning_curves(run_dir) is None
    assert build_learning_curves_view(None) == ()


def test_build_learning_curves_view_parses_folds(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    _write(
        run_dir / "learning_curves.json",
        {
            "schema_version": "learning_curves.v1",
            "folds": [
                {
                    "fold_id": 0,
                    "epochs": [1, 2, 3],
                    "train_loss": [0.9, 0.6, 0.4],
                    "validation_loss": [0.95, 0.65, 0.5],
                    "stopping_epoch": 2,
                }
            ],
        },
    )

    rows = build_learning_curves_view(load_run_learning_curves(run_dir))

    assert len(rows) == 1
    assert rows[0].stopping_epoch == 2
    assert rows[0].epochs == (1, 2, 3)


def test_build_window_accounting_rows_degrades_when_missing(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    assert load_run_window_accounting(run_dir) is None
    assert build_window_accounting_rows(None) == ()


def test_build_window_accounting_rows_parses_folds(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    _write(
        run_dir / "window_accounting.json",
        {
            "schema_version": "window_accounting.v1",
            "folds": [
                {
                    "fold_id": 0,
                    "fold_role": "TEST",
                    "candidate_end_rows": 100,
                    "windows_built": 80,
                    "windows_dropped_incomplete": 10,
                    "windows_dropped_gap": 5,
                    "windows_dropped_fold_boundary": 5,
                }
            ],
        },
    )

    rows = build_window_accounting_rows(load_run_window_accounting(run_dir))

    assert len(rows) == 1
    assert rows[0].fold_role == "TEST"
    assert rows[0].windows_built == 80


# --- Provenance + report link (T008) -------------------------------------------------


def test_load_run_provenance(tmp_path: Path) -> None:
    _write_run(tmp_path, metrics=_metrics())

    provenance = load_run_provenance(tmp_path, "r1")

    assert provenance is not None
    assert provenance.dataset_fingerprint == "fp-d1"
    assert provenance.estimator_family == "logistic_regression"
    assert provenance.estimator_seed == 42
    assert provenance.library == "sklearn"
    assert provenance.library_version == "1.4.0"


def test_load_run_provenance_unknown_run(tmp_path: Path) -> None:
    assert load_run_provenance(tmp_path, "missing") is None


def test_report_html_path_present_and_absent(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, metrics=_metrics())
    assert report_html_path(run_dir) is None

    (run_dir / "report.html").write_text("<html></html>", encoding="utf-8")
    path = report_html_path(run_dir)
    assert path is not None
    assert path.name == "report.html"


def _blank_finance() -> dict[str, object]:
    return {
        "mean_forward_return_by_decile": [0.0] * 10,
        "top_bottom_spread": 0.0,
        "hit_rate": 0.5,
        "coverage": 1.0,
        "mean_forward_return_selected": 0.0,
        "mean_forward_return_all": 0.0,
    }
