"""Tests for the Predictive Research catalog scan (S044-T001-T003)."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_app.caching.fingerprint import StorageFingerprint, cache_key_parts
from dashboard_app.catalog import list_predictive_catalog, list_runs, load_predictive_run_identity


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
        "time_range": {"start": "2024-01-01T00:00:00+00:00", "end": "2024-06-01T00:00:00+00:00"},
        "exclusion_counts": {
            "candidate_rows": 1000,
            "labelled_rows": 900,
            "incomplete_horizon": 50,
            "insufficient_data": 20,
            "null_features": 10,
        },
        "fold_summary": {
            "fold_count": 2,
            "role_counts": {"TRAIN": 600, "TEST": 200, "PURGED": 10, "EMBARGOED": 10},
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
        "decision_threshold": 0.5,
        "seed": 42,
        "folds": {
            "0": {
                "MODEL": {"statistical": {"roc_auc": 0.60}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.50}},
            },
            "1": {
                "MODEL": {"statistical": {"roc_auc": 0.62}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.51}},
            },
        },
        "pooled": {
            "MODEL": {"statistical": {"roc_auc": 0.61}},
            "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.58}},
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


_DEFAULT_METRICS = object()


def _write_run(
    root: Path, run_id: str = "r1", metrics: dict[str, object] | None | object = _DEFAULT_METRICS
) -> None:
    run_dir = root / "research" / "predictive_research" / "runs" / run_id
    _write(run_dir / "manifest.json", _run_manifest(run_id=run_id))
    resolved = _metrics(run_id=run_id) if metrics is _DEFAULT_METRICS else metrics
    if resolved is not None:
        _write(run_dir / "metrics.json", resolved)  # type: ignore[arg-type]


def test_valid_dataset_and_run_with_metrics(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    _write_run(tmp_path)

    catalog = list_predictive_catalog(tmp_path)

    assert catalog.issues == ()
    assert len(catalog.datasets) == 1
    dataset = catalog.datasets[0]
    assert dataset.dataset_id == "d1"
    assert dataset.dataset_fingerprint == "fp-d1"
    assert dataset.label_kind == "TRIPLE_BARRIER"
    assert dataset.horizon == "20b"
    assert dataset.run_count == 1

    assert len(catalog.runs) == 1
    run = catalog.runs[0]
    assert run.run_id == "r1"
    assert run.dataset_fingerprint == "fp-d1"
    assert run.family == "logistic_regression"
    assert run.has_metrics is True
    assert run.task_type == "CLASSIFICATION"
    assert run.primary_metric_name == "roc_auc"
    assert run.primary_metric_value == 0.61
    assert run.baseline_delta is not None
    assert round(run.baseline_delta, 2) == 0.03


def test_run_missing_metrics_json_is_flagged_not_dropped(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    _write_run(tmp_path, metrics=None)

    catalog = list_predictive_catalog(tmp_path)

    assert len(catalog.runs) == 1
    run = catalog.runs[0]
    assert run.has_metrics is False
    assert run.primary_metric_value is None
    assert run.baseline_delta is None
    # Missing metrics.json is not a scanner CatalogIssue by itself (D-S044-09
    # says the leaderboard omits it; only a corrupt metrics.json is an issue).
    assert catalog.issues == ()


def test_run_with_corrupt_metrics_json_records_issue(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    run_dir = tmp_path / "research" / "predictive_research" / "runs" / "r1"
    _write(run_dir / "manifest.json", _run_manifest())
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metrics.json").write_text("{not-json", encoding="utf-8")

    catalog = list_predictive_catalog(tmp_path)

    assert len(catalog.runs) == 1
    assert catalog.runs[0].has_metrics is False
    assert any("metrics.json" in issue.path for issue in catalog.issues)


def test_missing_permutation_baseline_yields_no_delta(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics = _metrics()
    pooled = metrics["pooled"]
    assert isinstance(pooled, dict)
    del pooled["RANDOM_PERMUTATION"]
    _write_run(tmp_path, metrics=metrics)

    catalog = list_predictive_catalog(tmp_path)

    run = catalog.runs[0]
    assert run.primary_metric_value == 0.61
    assert run.baseline_delta is None


def test_corrupt_dataset_manifest_is_an_issue_and_omitted(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "research" / "predictive_research" / "datasets" / "bad"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "manifest.json").write_text("{not-json", encoding="utf-8")

    catalog = list_predictive_catalog(tmp_path)

    assert catalog.datasets == ()
    assert any("bad" in issue.path for issue in catalog.issues)


def test_dataset_with_zero_runs_still_listed(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    catalog = list_predictive_catalog(tmp_path)

    assert len(catalog.datasets) == 1
    assert catalog.runs == ()


def test_run_with_dangling_dataset_id_is_still_returned(tmp_path: Path) -> None:
    _write_run(tmp_path)  # no matching dataset directory written

    catalog = list_predictive_catalog(tmp_path)

    assert catalog.datasets == ()
    assert len(catalog.runs) == 1
    assert catalog.runs[0].dataset_id == "d1"


def test_missing_predictive_research_dir_is_ignored(tmp_path: Path) -> None:
    catalog = list_predictive_catalog(tmp_path)
    assert catalog == list_predictive_catalog(tmp_path)
    assert catalog.datasets == ()
    assert catalog.runs == ()
    assert catalog.issues == ()


def test_list_runs_ignores_predictive_research_tree(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    _write_run(tmp_path)

    catalog = list_runs(tmp_path)

    assert catalog.runs == ()
    assert catalog.issues == ()


def test_load_predictive_run_identity(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    _write_run(tmp_path)

    identity = load_predictive_run_identity(tmp_path, "r1")

    assert identity is not None
    assert identity["dataset_fingerprint"] == "fp-d1"
    assert identity["library"] == "sklearn"
    assert identity["library_version"] == "1.4.0"
    assert identity["estimator_spec"]["family"] == "logistic_regression"


def test_load_predictive_run_identity_unknown_run(tmp_path: Path) -> None:
    assert load_predictive_run_identity(tmp_path, "missing") is None


def test_small_test_sample_flag(tmp_path: Path) -> None:
    _write_dataset(
        tmp_path,
        fold_summary={
            "fold_count": 1,
            "role_counts": {"TRAIN": 100, "TEST": 10},
            "per_fold": [{"fold_id": 0, "TRAIN": 100, "TEST": 10}],
        },
    )
    _write_run(tmp_path)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "SMALL_TEST_SAMPLE" in codes


def test_poor_calibration_flag(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics = _metrics()
    pooled = metrics["pooled"]
    assert isinstance(pooled, dict)
    pooled["MODEL"]["statistical"]["calibration_bins"] = [
        {"bin_index": 0, "count": 10, "mean_predicted": 0.9, "mean_observed": 0.2},
    ]
    _write_run(tmp_path, metrics=metrics)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "POOR_CALIBRATION" in codes


def test_large_train_test_gap_flag(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics = _metrics(fold_primary={"0": {"primary_gap": 0.5}})
    _write_run(tmp_path, metrics=metrics)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "LARGE_TRAIN_TEST_GAP" in codes


def test_unstable_across_folds_flag(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics = _metrics(
        folds={
            "0": {
                "MODEL": {"statistical": {"roc_auc": 0.50}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.50}},
            },
            "1": {
                "MODEL": {"statistical": {"roc_auc": 0.70}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.51}},
            },
        }
    )
    _write_run(tmp_path, metrics=metrics)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "UNSTABLE_ACROSS_FOLDS" in codes


def test_high_exclusion_share_flag(tmp_path: Path) -> None:
    _write_dataset(
        tmp_path,
        exclusion_counts={
            "candidate_rows": 100,
            "labelled_rows": 50,
            "incomplete_horizon": 40,
            "insufficient_data": 10,
            "null_features": 0,
        },
    )
    _write_run(tmp_path)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "HIGH_EXCLUSION_SHARE" in codes


def test_single_fold_dominance_flag(tmp_path: Path) -> None:
    _write_dataset(
        tmp_path,
        fold_summary={
            "fold_count": 2,
            "role_counts": {"TRAIN": 600, "TEST": 1000},
            "per_fold": [
                {"fold_id": 0, "TRAIN": 300, "TEST": 800},
                {"fold_id": 1, "TRAIN": 300, "TEST": 200},
            ],
        },
    )
    _write_run(tmp_path)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "SINGLE_FOLD_DOMINANCE" in codes


def test_within_permutation_spread_flag(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    metrics = _metrics(
        pooled={
            "MODEL": {"statistical": {"roc_auc": 0.55}},
            "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.58}},
        }
    )
    _write_run(tmp_path, metrics=metrics)

    catalog = list_predictive_catalog(tmp_path)
    codes = {flag.code for flag in catalog.runs[0].quality_flags}
    assert "WITHIN_PERMUTATION_SPREAD" in codes


def test_cache_key_parts_dataset_id_distinguishes_keys() -> None:
    fingerprint = StorageFingerprint(token="tok", storage_root="/root")
    without = cache_key_parts(fingerprint=fingerprint, run_id="r1")
    with_dataset = cache_key_parts(fingerprint=fingerprint, run_id="r1", dataset_id="d1")
    assert without != with_dataset
