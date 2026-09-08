"""Unit tests for Analyst Verdict Artifact fact extraction (ADR-0032, S057-T003).

Fixtures here are hand-built, synthetic, and shaped exactly like the real
``metrics.json`` / dataset ``manifest.json`` / ``importance.json`` payloads
this module reads (per `PredictiveMetricsReport`, `PredictiveDatasetManifest`
and `ImportanceTrace`'s own schemas) -- never a read of `user_data/` or the
network (ADR-0023 SS8).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import MappingProxyType

import numpy as np
import pytest

from trading_framework.research.datasets.predictive import PredictiveDatasetManifest
from trading_framework.research.predictive import (
    VERDICT_RULES_V1,
    RunVerdict,
    TaskType,
    evaluate_verdict,
    extract_verdict_facts,
)
from trading_framework.research.predictive.importance import (
    FoldImportanceRecord,
    FoldPrimaryGap,
    ImportanceTrace,
    PermutationImportance,
)
from trading_framework.research.predictive.metrics import (
    FinanceMetrics,
    MetricSource,
    PredictiveMetricsReport,
    SourceMetrics,
    StatisticalMetrics,
    finance_metrics,
)
from trading_framework.research.predictive.sample import (
    PredictiveTask,
    SampleKind,
    SampleProvenance,
)

_RETURNS = np.array([0.01, -0.02, 0.03, 0.04, -0.01], dtype=np.float64)


def _finance() -> FinanceMetrics:
    return finance_metrics(_RETURNS, _RETURNS, threshold=0.0)


def _source(*, roc_auc: float | None = None, spearman_ic: float | None = None) -> SourceMetrics:
    return SourceMetrics(
        statistical=StatisticalMetrics(roc_auc=roc_auc, spearman_ic=spearman_ic),
        finance=_finance(),
    )


def _regression_metrics_report(
    *,
    pooled_model: float = 0.05,
    pooled_permutation: float = 0.01,
    fold_model: dict[str, float] | None = None,
    fold_permutation: dict[str, float] | None = None,
    fold_primary: dict[str, dict[str, float | None]] | None = None,
) -> PredictiveMetricsReport:
    fold_model = fold_model or {"1": 0.06, "2": 0.05, "3": 0.04}
    fold_permutation = fold_permutation or {"1": 0.01, "2": 0.0, "3": 0.02}
    folds = {
        fold_id: {
            MetricSource.MODEL.value: _source(spearman_ic=fold_model[fold_id]),
            MetricSource.CONSTANT_MEAN.value: _source(spearman_ic=0.0),
            MetricSource.RANDOM_PERMUTATION.value: _source(spearman_ic=fold_permutation[fold_id]),
        }
        for fold_id in fold_model
    }
    pooled = {
        MetricSource.MODEL.value: _source(spearman_ic=pooled_model),
        MetricSource.CONSTANT_MEAN.value: _source(spearman_ic=0.0),
        MetricSource.RANDOM_PERMUTATION.value: _source(spearman_ic=pooled_permutation),
    }
    return PredictiveMetricsReport(
        schema_version="predictive_metrics.v1",
        run_id="0123456789abcdef",
        task_type=TaskType.REGRESSION,
        decision_threshold=0.0,
        seed=7,
        folds=folds,
        pooled=pooled,
        fold_primary=fold_primary,
    )


def _classification_metrics_report(
    *,
    pooled_model: float = 0.55,
    pooled_permutation: float = 0.50,
) -> PredictiveMetricsReport:
    fold_model = {"1": 0.56, "2": 0.55, "3": 0.54}
    fold_permutation = {"1": 0.50, "2": 0.50, "3": 0.50}
    folds = {
        fold_id: {
            MetricSource.MODEL.value: _source(roc_auc=fold_model[fold_id]),
            MetricSource.MAJORITY_CLASS.value: _source(roc_auc=0.5),
            MetricSource.RANDOM_PERMUTATION.value: _source(roc_auc=fold_permutation[fold_id]),
        }
        for fold_id in fold_model
    }
    pooled = {
        MetricSource.MODEL.value: _source(roc_auc=pooled_model),
        MetricSource.MAJORITY_CLASS.value: _source(roc_auc=0.5),
        MetricSource.RANDOM_PERMUTATION.value: _source(roc_auc=pooled_permutation),
    }
    return PredictiveMetricsReport(
        schema_version="predictive_metrics.v1",
        run_id="fedcba9876543210",
        task_type=TaskType.CLASSIFICATION,
        decision_threshold=0.5,
        seed=7,
        folds=folds,
        pooled=pooled,
    )


def _dataset_manifest(
    *,
    role_counts: dict[str, int] | None = None,
    embargo_span: str = "1d",
    label_horizon: str = "1h",
    per_fold_test_rows: dict[int, int] | None = None,
    exclusion_counts: dict[str, int] | None = None,
    sample_provenance: SampleProvenance | None = None,
) -> PredictiveDatasetManifest:
    role_counts = role_counts or {"TRAIN": 500, "TEST": 300, "PURGED": 10, "EMBARGOED": 5}
    per_fold_test_rows = per_fold_test_rows or {1: 100, 2: 100, 3: 100}
    exclusion_counts = exclusion_counts or {
        "candidate_rows": 1000,
        "labelled_rows": 900,
        "incomplete_horizon": 50,
        "insufficient_data": 30,
        "null_features": 20,
    }
    study_spec = {
        "study_id": "s",
        "split": {"test_span": "1d", "embargo_span": embargo_span, "fold_count": 3},
        "label": {"kind": "REGRESSION", "horizon": label_horizon},
    }
    fold_summary = {
        "fold_count": len(per_fold_test_rows),
        "role_counts": dict(role_counts),
        "per_fold": [
            {"fold_id": fold_id, "TRAIN": 100, "TEST": test_rows, "PURGED": 3, "EMBARGOED": 2}
            for fold_id, test_rows in per_fold_test_rows.items()
        ],
    }
    return PredictiveDatasetManifest(
        schema_version="predictive_dataset.v2",
        dataset_id="0123456789abcdef",
        study_spec=study_spec,
        definition_hash="a" * 64,
        dataset_fingerprint="b" * 64,
        source_dataset_ref="BTCUSDT.P@1",
        time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
        time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
        exclusion_counts=exclusion_counts,
        fold_summary=fold_summary,
        framework_version="0.0.0-test",
        created_at_utc=datetime(2024, 6, 2, tzinfo=UTC),
        sample_provenance=sample_provenance,
    )


def _importance_trace(*, feature_values: dict[str, float] | None = None) -> ImportanceTrace:
    feature_values = feature_values or {"feature_a": 0.02, "feature_b": -0.01}
    record = FoldImportanceRecord(
        fold_id=1,
        native=None,
        permutation=PermutationImportance(
            feature_names=tuple(feature_values),
            importances_mean=tuple(feature_values.values()),
            importances_std=tuple(0.0 for _ in feature_values),
            n_repeats=5,
            seed=7,
            metric="spearman_ic",
        ),
        primary_gap=FoldPrimaryGap(train_primary=0.06, test_primary=0.05, primary_gap=0.01),
    )
    return ImportanceTrace(metric="spearman_ic", n_repeats=5, folds=(record,))


# ---------------------------------------------------------------------------
# Every fact is extracted with a real source, and the resulting VerdictFacts
# drives the same verdict evaluate_verdict would produce from a hand-built
# VerdictFacts with equivalent values.
# ---------------------------------------------------------------------------


def test_extraction_populates_every_declared_fact_with_its_source() -> None:
    metrics = _regression_metrics_report(
        fold_primary={
            "1": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "2": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "3": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
        }
    )
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)

    assert facts.task_type is TaskType.REGRESSION
    assert facts.pooled_model_primary == pytest.approx(0.05)
    assert facts.pooled_random_permutation_primary == pytest.approx(0.01)
    assert facts.fold_model_primary == {"1": 0.06, "2": 0.05, "3": 0.04}
    assert facts.fold_random_permutation_primary == {"1": 0.01, "2": 0.0, "3": 0.02}
    assert facts.fold_train_primary == {"1": 0.05, "2": 0.05, "3": 0.05}
    assert facts.fold_test_primary == {"1": 0.05, "2": 0.05, "3": 0.05}
    assert facts.fold_test_row_counts == {"1": 100, "2": 100, "3": 100}
    assert facts.fold_count == 3
    assert facts.role_counts == {"TRAIN": 500, "TEST": 300, "PURGED": 10, "EMBARGOED": 5}
    assert facts.embargo_span == timedelta(days=1)
    assert facts.label_horizon == timedelta(hours=1)
    assert facts.minority_class_share is None  # REGRESSION: not applicable
    assert facts.exclusion_counts == {
        "candidate_rows": 1000,
        "labelled_rows": 900,
        "incomplete_horizon": 50,
        "insufficient_data": 30,
        "null_features": 20,
    }
    assert facts.sample_provenance is None
    assert facts.feature_importance == {}
    assert facts.feature_importance_missing == (
        "importance.json not present (optional artifact, D-S057-05)"
    )

    # Several facts, not just one, must record the real source artifact.
    assert facts.sources["pooled_model_primary"] == (
        "metrics.json:pooled.MODEL.statistical.spearman_ic"
    )
    assert facts.sources["pooled_random_permutation_primary"] == (
        "metrics.json:pooled.RANDOM_PERMUTATION.statistical.spearman_ic"
    )
    assert facts.sources["fold_test_row_counts"] == (
        "dataset manifest.json:fold_summary.per_fold[].TEST"
    )
    assert facts.sources["role_counts"] == "dataset manifest.json:fold_summary.role_counts"
    assert facts.sources["embargo_span"] == "dataset manifest.json:study_spec.split.embargo_span"
    assert facts.sources["label_horizon"] == "dataset manifest.json:study_spec.label.horizon"
    assert facts.sources["exclusion_counts"] == "dataset manifest.json:exclusion_counts"
    assert "absent" in facts.sources["feature_importance"]


def test_extraction_reproduces_evaluate_verdict_pass_from_clean_fixtures() -> None:
    metrics = _regression_metrics_report(
        fold_primary={
            "1": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "2": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "3": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
        }
    )
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)
    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    assert report.verdict is RunVerdict.PASS


# ---------------------------------------------------------------------------
# Baseline delta / fold win-rate use the SAME primary-metric convention as
# research/reporting/predictive/quality.py::primary_metric_name — this test
# would catch a hardcoded/wrong metric name (e.g. always roc_auc).
# ---------------------------------------------------------------------------


def test_classification_extraction_uses_roc_auc_not_spearman_ic() -> None:
    metrics = _classification_metrics_report(pooled_model=0.60, pooled_permutation=0.50)
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, pooled_test_labels=[1.0] * 40 + [0.0] * 60
    )

    # roc_auc was set; spearman_ic was never populated on these StatisticalMetrics,
    # so a hardcoded spearman_ic read would silently produce None here instead.
    assert facts.pooled_model_primary == pytest.approx(0.60)
    assert facts.pooled_random_permutation_primary == pytest.approx(0.50)
    assert facts.sources["pooled_model_primary"] == "metrics.json:pooled.MODEL.statistical.roc_auc"


def test_regression_extraction_uses_spearman_ic_not_roc_auc() -> None:
    metrics = _regression_metrics_report(pooled_model=0.07, pooled_permutation=0.02)
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)

    assert facts.pooled_model_primary == pytest.approx(0.07)
    assert facts.pooled_random_permutation_primary == pytest.approx(0.02)
    assert facts.sources["pooled_model_primary"] == (
        "metrics.json:pooled.MODEL.statistical.spearman_ic"
    )


def test_fold_win_counting_uses_the_same_metric_as_baseline_delta() -> None:
    """A fold_model_primary / fold_random_permutation_primary mismatch in metric
    choice would silently break O1-O4's fold_win_rate; assert both come from the
    declared primary metric on a CLASSIFICATION run.
    """
    metrics = _classification_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, pooled_test_labels=[1.0] * 40 + [0.0] * 60
    )

    assert facts.fold_model_primary == {"1": 0.56, "2": 0.55, "3": 0.54}
    assert facts.fold_random_permutation_primary == {"1": 0.50, "2": 0.50, "3": 0.50}
    report = evaluate_verdict(facts, VERDICT_RULES_V1)
    o1 = next(e for e in report.evaluations if e.rule_id == "O1")
    assert o1.observed["fold_win_rate"] == 1.0


# ---------------------------------------------------------------------------
# Feature importance drives no rule, even with absurd values.
# ---------------------------------------------------------------------------


def test_absurd_feature_importance_does_not_change_the_verdict() -> None:
    metrics = _regression_metrics_report(
        fold_primary={
            "1": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "2": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "3": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
        }
    )
    manifest = _dataset_manifest()

    normal = extract_verdict_facts(
        metrics=metrics,
        dataset_manifest=manifest,
        importance=_importance_trace(feature_values={"feature_a": 0.001, "feature_b": -0.0005}),
    )
    absurd = extract_verdict_facts(
        metrics=metrics,
        dataset_manifest=manifest,
        importance=_importance_trace(
            feature_values={"feature_a": 999_999.0, "feature_b": -999_999.0}
        ),
    )

    assert normal.feature_importance != absurd.feature_importance  # fixtures really differ
    normal_report = evaluate_verdict(normal, VERDICT_RULES_V1)
    absurd_report = evaluate_verdict(absurd, VERDICT_RULES_V1)
    assert normal_report.verdict is absurd_report.verdict
    assert normal_report.to_dict()["evaluations"] == absurd_report.to_dict()["evaluations"]


# ---------------------------------------------------------------------------
# Missing optional importance.json: total extraction, never an exception,
# never a forced INCONCLUSIVE.
# ---------------------------------------------------------------------------


def test_missing_importance_extracts_successfully_with_a_named_marker() -> None:
    metrics = _regression_metrics_report(
        fold_primary={
            "1": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "2": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
            "3": {"train_primary": 0.05, "test_primary": 0.05, "primary_gap": 0.0},
        }
    )
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest, importance=None)

    assert facts.feature_importance == {}
    assert facts.feature_importance_missing is not None

    report = evaluate_verdict(facts, VERDICT_RULES_V1)
    assert report.verdict is RunVerdict.PASS  # not forced INCONCLUSIVE by the missing optional


def test_present_importance_clears_the_missing_marker() -> None:
    metrics = _regression_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, importance=_importance_trace()
    )

    assert facts.feature_importance_missing is None
    assert facts.feature_importance == {"1": {"feature_a": 0.02, "feature_b": -0.01}}


# ---------------------------------------------------------------------------
# Minority-class share (Finding 3 / D-S057-05).
# ---------------------------------------------------------------------------


def test_minority_class_share_computed_from_pooled_test_labels_on_classification() -> None:
    metrics = _classification_metrics_report()
    manifest = _dataset_manifest()
    labels = [1.0] * 20 + [0.0] * 80  # minority share 0.20

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, pooled_test_labels=labels
    )

    assert facts.minority_class_share == pytest.approx(0.20)
    assert facts.sources["minority_class_share"] == (
        "dataset features.parquet:TEST-role label column"
    )


def test_minority_class_share_none_when_labels_not_supplied_on_classification() -> None:
    metrics = _classification_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)

    assert facts.minority_class_share is None
    assert "not provided" in facts.sources["minority_class_share"]


def test_minority_class_share_not_applicable_on_regression_even_if_labels_supplied() -> None:
    metrics = _regression_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, pooled_test_labels=[1.0, 0.0, 1.0]
    )

    assert facts.minority_class_share is None
    assert "not applicable" in facts.sources["minority_class_share"]


# ---------------------------------------------------------------------------
# sample_provenance (recorded only) — present vs absent (v1 schema) manifests.
# ---------------------------------------------------------------------------


def test_sample_provenance_recorded_when_present() -> None:
    metrics = _regression_metrics_report()
    provenance = SampleProvenance(
        kind=SampleKind.EVERY_BAR,
        task=PredictiveTask.FORWARD_RETURN,
        universe_row_count=1000,
        resolved_row_count=1000,
        drop_counts={},
    )
    manifest = _dataset_manifest(sample_provenance=provenance)

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)

    assert facts.sample_provenance is not None
    assert facts.sample_provenance["kind"] == SampleKind.EVERY_BAR.value
    assert facts.sources["sample_provenance"] == "dataset manifest.json:sample_provenance"


def test_sample_provenance_none_when_absent_v1_manifest() -> None:
    metrics = _regression_metrics_report()
    manifest = _dataset_manifest(sample_provenance=None)

    facts = extract_verdict_facts(metrics=metrics, dataset_manifest=manifest)

    assert facts.sample_provenance is None
    assert "absent" in facts.sources["sample_provenance"]


# ---------------------------------------------------------------------------
# VerdictFacts immutability and total extraction (no exception on ordinary
# missing-optional inputs).
# ---------------------------------------------------------------------------


def test_extraction_never_raises_for_missing_optional_importance_or_labels() -> None:
    metrics = _regression_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics,
        dataset_manifest=manifest,
        pooled_test_labels=None,
        importance=None,
    )

    assert facts is not None


def test_facts_mappings_are_read_only() -> None:
    metrics = _regression_metrics_report()
    manifest = _dataset_manifest()

    facts = extract_verdict_facts(
        metrics=metrics, dataset_manifest=manifest, importance=_importance_trace()
    )

    assert isinstance(facts.sources, MappingProxyType)
    assert isinstance(facts.feature_importance, MappingProxyType)
    assert isinstance(facts.exclusion_counts, MappingProxyType)
