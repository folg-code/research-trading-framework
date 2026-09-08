"""Analyst Verdict Artifact: vocabulary, rule set, and pure evaluation (ADR-0032).

This module DECLARES the eight-value verdict vocabulary (:class:`RunVerdict`),
the frozen ``verdict_rules.v1`` rule set (:class:`VerdictRuleSet`), the
extracted-input contract (:class:`VerdictFacts`), and the pure cascade
(:func:`evaluate_verdict`) that turns facts into a :class:`VerdictReport`.

Library-free, like ``metrics.py``: no polars/numpy dependency is required for
this module's own logic (it operates on plain Python values), and it must gain
no import of scikit-learn, XGBoost, LightGBM, CatBoost, torch,
``trading_framework.signal_model``, ``trading_framework.strategy``,
``trading_framework.application`` or ``trading_framework.research.reporting``
(ADR-0032 §5, enforced by ``tests/unit/test_architecture_boundaries.py``).

:func:`extract_verdict_facts` (S057-T003) turns already-parsed, in-memory
representations of those artifacts (a
:class:`~trading_framework.research.predictive.metrics.PredictiveMetricsReport`,
a dataset
:class:`~trading_framework.research.datasets.predictive.PredictiveDatasetManifest`,
already-loaded TEST labels, an optional already-loaded
:class:`~trading_framework.research.predictive.importance.ImportanceTrace`)
into a :class:`VerdictFacts`. It performs no file I/O itself — reading
``metrics.json``, a dataset envelope, ``features.parquet`` and
``importance.json`` off disk is
``application/predictive_research/evaluate_run_verdict.py``'s job
(S057-T004), which parses each artifact and hands the already-built objects
to this function. File I/O and sidecar persistence stay out of scope here.

Rule order is fixed and part of the contract: ``R2, R3, R4, R1``, then
``O1..O4`` (D-S057-06). The first rejection rule that fires determines the
verdict; every one of the eight rules is still evaluated and recorded in the
returned :class:`VerdictReport`. A rule whose required fact is missing from
``VerdictFacts`` is recorded as not evaluated (never as not-fired, never
silently skipped), and the overall verdict is ``INCONCLUSIVE`` naming the
missing input, unless an earlier rejection rule already fired.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.importance import ImportanceTrace
from trading_framework.research.predictive.metrics import (
    MetricSource,
    PredictiveMetricsReport,
    SourceMetrics,
)
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.time.models.timeframe import Timeframe

if TYPE_CHECKING:
    # Deferred to TYPE_CHECKING only: `research.datasets.predictive` imports
    # `research.predictive.exclusions` / `.sample` / `.splitting` (submodules
    # of THIS package), so an eager, runtime import here — triggered while
    # `research/predictive/__init__.py` is still executing — is a genuine
    # circular import, not merely an undesirable layering. `from __future__
    # import annotations` (top of this file) makes every annotation below a
    # deferred string, so this Protocol-free type-only import is safe; nothing
    # at runtime needs the real class, only structural attribute access
    # (`.fold_summary`, `.study_spec`, `.exclusion_counts`,
    # `.sample_provenance`) on whatever object the caller passes in.
    from trading_framework.research.datasets.predictive import PredictiveDatasetManifest

RULE_SET_VERSION_V1 = "verdict_rules.v1"

_CLASSIFICATION_NEUTRAL = 0.5
_REGRESSION_NEUTRAL = 0.0


class RunVerdict(StrEnum):
    """The whole verdict vocabulary — eight values, exactly (ADR-0032 §1).

    No ninth value, no severity score, no numeric grade, no colour, no
    ordering key, no "confidence" field is added in v1. ``REJECTED_*`` means
    "not interpretable as evidence", never "this model is bad" or "banned".
    None of the eight values means validated, approved, promotable,
    tradeable, live-ready or safe.
    """

    # OUTCOME group — reached only when no rejection rule fired.
    PASS = "PASS"
    WEAK_PASS = "WEAK_PASS"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAIL = "FAIL"

    # REJECTION group — dominates the outcome group entirely.
    REJECTED_OVERFIT = "REJECTED_OVERFIT"
    REJECTED_LEAKAGE_RISK = "REJECTED_LEAKAGE_RISK"
    REJECTED_LOW_SAMPLE = "REJECTED_LOW_SAMPLE"
    REJECTED_CONCENTRATION = "REJECTED_CONCENTRATION"


@dataclass(frozen=True, slots=True)
class VerdictRuleSet:
    """The frozen, versioned ``verdict_rules.v1`` thresholds (ADR-0032 §2, D-S057-06).

    Every threshold used anywhere in :func:`evaluate_verdict` lives here, by
    name. Changing any number requires a new ``version`` string — that is a
    one-file diff, never a silent value change. Callers must use
    :data:`VERDICT_RULES_V1`; there is no override file, no per-study rule
    set, and no keyword argument anywhere in this package's public API that
    changes a threshold in v1.
    """

    version: str = RULE_SET_VERSION_V1
    # R1 REJECTED_OVERFIT: median(train - test) > overfit_gap_ratio * effect_size_pooled.
    overfit_gap_ratio: float = 1.0
    # R3 REJECTED_LOW_SAMPLE.
    min_test_rows: int = 30
    min_folds: int = 3
    min_minority_class_share: float = 0.10
    # R4 REJECTED_CONCENTRATION.
    max_single_fold_test_share: float = 0.60
    # O1/O2/O3 fold win-rate cutoffs.
    min_fold_win_rate: float = 2.0 / 3.0
    # R2 REJECTED_LEAKAGE_RISK implausibility ceiling.
    classification_roc_auc_ceiling: float = 0.75
    regression_spearman_ic_ceiling: float = 0.30

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "overfit_gap_ratio": self.overfit_gap_ratio,
            "min_test_rows": self.min_test_rows,
            "min_folds": self.min_folds,
            "min_minority_class_share": self.min_minority_class_share,
            "max_single_fold_test_share": self.max_single_fold_test_share,
            "min_fold_win_rate": self.min_fold_win_rate,
            "classification_roc_auc_ceiling": self.classification_roc_auc_ceiling,
            "regression_spearman_ic_ceiling": self.regression_spearman_ic_ceiling,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VerdictRuleSet:
        return cls(
            version=str(payload["version"]),
            overfit_gap_ratio=float(payload["overfit_gap_ratio"]),
            min_test_rows=int(payload["min_test_rows"]),
            min_folds=int(payload["min_folds"]),
            min_minority_class_share=float(payload["min_minority_class_share"]),
            max_single_fold_test_share=float(payload["max_single_fold_test_share"]),
            min_fold_win_rate=float(payload["min_fold_win_rate"]),
            classification_roc_auc_ceiling=float(payload["classification_roc_auc_ceiling"]),
            regression_spearman_ic_ceiling=float(payload["regression_spearman_ic_ceiling"]),
        )


#: The one frozen v1 rule set. Callers evaluate against this constant, never
#: a hand-built :class:`VerdictRuleSet` (ADR-0032 §2).
VERDICT_RULES_V1 = VerdictRuleSet()


@dataclass(frozen=True, slots=True)
class VerdictFacts:
    """Extracted inputs :func:`evaluate_verdict` reads (D-S057-05's fact table).

    Every field is optional except ``task_type``: a rule whose required
    fact(s) are ``None`` / empty is recorded as not evaluated rather than
    guessed at. Per-fold mappings key on the fold id (``str``, matching
    ``metrics.json``'s own fold-id keys). ``fold_train_primary`` /
    ``fold_test_primary`` correspond to ``metrics.json``'s optional
    ``fold_primary`` field (train/test primary-metric values per fold) — the
    realistic missing-input case R1 depends on.

    This dataclass is built by hand in this package's own tests, or produced
    for real by :func:`extract_verdict_facts` (S057-T003) from an already-parsed
    ``PredictiveMetricsReport`` / dataset manifest / ``importance.json``.

    ``exclusion_counts``, ``sample_provenance`` and ``feature_importance`` are
    RECORDED ONLY (D-S057-05): no rule in ``verdict_rules.v1`` reads them.
    ``feature_importance_missing`` names why ``feature_importance`` is empty
    when ``importance.json`` was not available to the extractor — the ONE
    optional artifact in the fact table (D-S057-05); its absence never raises
    and never forces the rule cascade to ``INCONCLUSIVE`` on its own, because
    no rule depends on it.

    ``sources`` maps each populated fact's field name to the artifact (and, for
    ``metrics.json``/dataset ``manifest.json`` facts, the exact path within it)
    the value was read from — the field-level analogue of
    :attr:`RuleEvaluation.source`, and what makes "reproducible from the
    persisted artifacts alone" (ADR-0032 §5) a fact a reader can point at,
    not just claim.
    """

    task_type: TaskType
    pooled_model_primary: float | None = None
    pooled_random_permutation_primary: float | None = None
    fold_model_primary: Mapping[str, float] = field(default_factory=dict)
    fold_random_permutation_primary: Mapping[str, float] = field(default_factory=dict)
    fold_train_primary: Mapping[str, float] = field(default_factory=dict)
    fold_test_primary: Mapping[str, float] = field(default_factory=dict)
    fold_test_row_counts: Mapping[str, int] = field(default_factory=dict)
    fold_count: int | None = None
    role_counts: Mapping[str, int] | None = None
    embargo_span: timedelta | None = None
    label_horizon: timedelta | None = None
    minority_class_share: float | None = None
    exclusion_counts: Mapping[str, int] = field(default_factory=dict)
    sample_provenance: Mapping[str, Any] | None = None
    feature_importance: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    feature_importance_missing: str | None = None
    sources: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "fold_model_primary", MappingProxyType(dict(self.fold_model_primary))
        )
        object.__setattr__(
            self,
            "fold_random_permutation_primary",
            MappingProxyType(dict(self.fold_random_permutation_primary)),
        )
        object.__setattr__(
            self, "fold_train_primary", MappingProxyType(dict(self.fold_train_primary))
        )
        object.__setattr__(
            self, "fold_test_primary", MappingProxyType(dict(self.fold_test_primary))
        )
        object.__setattr__(
            self, "fold_test_row_counts", MappingProxyType(dict(self.fold_test_row_counts))
        )
        if self.role_counts is not None:
            object.__setattr__(self, "role_counts", MappingProxyType(dict(self.role_counts)))
        object.__setattr__(self, "exclusion_counts", MappingProxyType(dict(self.exclusion_counts)))
        if self.sample_provenance is not None:
            object.__setattr__(
                self, "sample_provenance", MappingProxyType(dict(self.sample_provenance))
            )
        object.__setattr__(
            self,
            "feature_importance",
            MappingProxyType(
                {
                    fold_id: MappingProxyType(dict(values))
                    for fold_id, values in self.feature_importance.items()
                }
            ),
        )
        object.__setattr__(self, "sources", MappingProxyType(dict(self.sources)))
        if self.fold_count is not None and self.fold_count < 0:
            msg = "fold_count must be non-negative"
            raise PredictiveSpecError(msg)
        if self.minority_class_share is not None and not (0.0 <= self.minority_class_share <= 1.0):
            msg = "minority_class_share must be within [0, 1]"
            raise PredictiveSpecError(msg)
        for fold_id, count in self.fold_test_row_counts.items():
            if count < 0:
                msg = f"fold_test_row_counts[{fold_id!r}] must be non-negative"
                raise PredictiveSpecError(msg)


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    """One rule's recorded outcome.

    ADR-0032 §4: ``rule_id, fired, observed, threshold, inputs_used``.

    ``observed`` / ``threshold`` are small named mappings of the quantities
    the rule compared (a rule may combine several sub-conditions, e.g. R2's
    three ``ANY OF`` clauses) rather than a single scalar, so the full
    comparison is recorded, not just its boolean result. ``source`` names the
    :class:`VerdictFacts` field(s) the rule reads. When ``evaluated`` is
    ``False`` (a required fact was missing), ``fired`` is always ``False``,
    ``observed`` / ``threshold`` are empty, and ``missing_input`` names what
    was missing.
    """

    rule_id: str
    fired: bool
    observed: Mapping[str, Any]
    threshold: Mapping[str, Any]
    source: str
    evaluated: bool = True
    missing_input: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed", MappingProxyType(dict(self.observed)))
        object.__setattr__(self, "threshold", MappingProxyType(dict(self.threshold)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "fired": self.fired,
            "observed": dict(self.observed),
            "threshold": dict(self.threshold),
            "source": self.source,
            "evaluated": self.evaluated,
            "missing_input": self.missing_input,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RuleEvaluation:
        return cls(
            rule_id=str(payload["rule_id"]),
            fired=bool(payload["fired"]),
            observed=dict(payload.get("observed", {})),
            threshold=dict(payload.get("threshold", {})),
            source=str(payload["source"]),
            evaluated=bool(payload.get("evaluated", True)),
            missing_input=(
                None if payload.get("missing_input") is None else str(payload["missing_input"])
            ),
        )


@dataclass(frozen=True, slots=True)
class VerdictReport:
    """The full, deterministic result of one :func:`evaluate_verdict` call.

    ``evaluations`` records all eight rules in fixed order (``R2, R3, R4,
    R1, O1, O2, O3, O4``) — not only the one that determined ``verdict``.
    Carries no wall-clock field (D-S057-07): same ``VerdictFacts`` and
    ``VerdictRuleSet`` in, byte-identical ``to_dict()`` output out.
    """

    verdict: RunVerdict
    rule_set_version: str
    evaluations: tuple[RuleEvaluation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "rule_set_version": self.rule_set_version,
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VerdictReport:
        try:
            verdict = RunVerdict(str(payload["verdict"]))
        except ValueError as exc:
            msg = f"invalid verdict: {payload.get('verdict')!r}"
            raise PredictiveSpecError(msg) from exc
        evaluations_raw = payload.get("evaluations", [])
        return cls(
            verdict=verdict,
            rule_set_version=str(payload["rule_set_version"]),
            evaluations=tuple(RuleEvaluation.from_dict(item) for item in evaluations_raw),
        )


_REJECTION_VERDICT_BY_RULE_ID: Mapping[str, RunVerdict] = MappingProxyType(
    {
        "R2": RunVerdict.REJECTED_LEAKAGE_RISK,
        "R3": RunVerdict.REJECTED_LOW_SAMPLE,
        "R4": RunVerdict.REJECTED_CONCENTRATION,
        "R1": RunVerdict.REJECTED_OVERFIT,
    }
)


def evaluate_verdict(facts: VerdictFacts, rules: VerdictRuleSet) -> VerdictReport:
    """Evaluate the fixed ``verdict_rules.v1`` cascade over ``facts`` (ADR-0032 §2).

    Pure: no randomness, no clock, no environment read. Evaluation order is
    fixed (``R2, R3, R4, R1``, then ``O1..O4``); every rule is evaluated and
    recorded regardless of which one determines the final verdict. The first
    rejection rule (in that order) that fires wins. If no rejection rule
    fires but one could not be evaluated because a required fact is missing,
    the verdict is ``INCONCLUSIVE`` naming that missing input — never a
    silently skipped rule, never ``PASS``.
    """
    r2 = _evaluate_r2(facts, rules)
    r3 = _evaluate_r3(facts, rules)
    r4 = _evaluate_r4(facts, rules)
    r1 = _evaluate_r1(facts, rules)
    o1, o2, o3, o4, outcome_missing = _evaluate_outcome_rules(facts, rules)
    evaluations = (r2, r3, r4, r1, o1, o2, o3, o4)

    verdict: RunVerdict | None = None
    missing_rejection: RuleEvaluation | None = None
    for evaluation in (r2, r3, r4, r1):
        if not evaluation.evaluated:
            if missing_rejection is None:
                missing_rejection = evaluation
            continue
        if evaluation.fired and verdict is None:
            verdict = _REJECTION_VERDICT_BY_RULE_ID[evaluation.rule_id]

    if verdict is not None:
        return VerdictReport(
            verdict=verdict, rule_set_version=rules.version, evaluations=evaluations
        )

    if missing_rejection is not None:
        return VerdictReport(
            verdict=RunVerdict.INCONCLUSIVE, rule_set_version=rules.version, evaluations=evaluations
        )

    if outcome_missing is not None:
        return VerdictReport(
            verdict=RunVerdict.INCONCLUSIVE, rule_set_version=rules.version, evaluations=evaluations
        )

    for evaluation, outcome_verdict in (
        (o1, RunVerdict.PASS),
        (o2, RunVerdict.WEAK_PASS),
        (o3, RunVerdict.INCONCLUSIVE),
        (o4, RunVerdict.FAIL),
    ):
        if evaluation.fired:
            return VerdictReport(
                verdict=outcome_verdict, rule_set_version=rules.version, evaluations=evaluations
            )

    # Unreachable: O1..O4 are mutually exclusive and exhaustive once
    # pooled/fold facts are present (checked via outcome_missing above).
    msg = "no outcome rule fired despite complete baseline facts"
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Fact extraction (S057-T003, D-S057-05).
#
# `extract_verdict_facts` is pure: every argument is already an in-memory,
# already-parsed representation of a persisted artifact. It performs no file
# I/O — reading `metrics.json`, a dataset envelope, `features.parquet` and
# `importance.json` off disk is the caller's job
# (`application/predictive_research/evaluate_run_verdict.py`, S057-T004).
# ---------------------------------------------------------------------------


def extract_verdict_facts(
    *,
    metrics: PredictiveMetricsReport,
    dataset_manifest: PredictiveDatasetManifest,
    pooled_test_labels: Sequence[float] | None = None,
    importance: ImportanceTrace | None = None,
) -> VerdictFacts:
    """Turn already-parsed persisted artifacts into a :class:`VerdictFacts` (D-S057-05).

    ``metrics`` is the in-memory ``metrics.json`` representation. ``dataset_manifest``
    is the dataset envelope's already-parsed manifest, supplying ``study_spec``,
    ``fold_summary`` and ``exclusion_counts``. ``pooled_test_labels`` is the
    pooled TEST-role label column read from the dataset's ``features.parquet``
    (Finding 3) — required only to compute ``minority_class_share`` on a
    ``CLASSIFICATION`` task; ``None`` is a legitimate value (e.g. a
    ``REGRESSION`` task, or a caller that has not read the parquet), never an
    error. ``importance`` is the ONE optional artifact (D-S057-05): ``None``
    means ``importance.json`` was not present, and produces a named
    ``feature_importance_missing`` marker rather than raising, because no rule
    reads feature importance in v1.

    The baseline delta and per-fold win counting both read the SAME primary
    metric — ``roc_auc`` for ``CLASSIFICATION``, ``spearman_ic`` for
    ``REGRESSION`` — matching the convention already declared by
    ``research/reporting/predictive/quality.py::primary_metric_name`` /
    ``primary_metric_value`` exactly. This module cannot import
    ``research.reporting`` (ADR-0032 §5), so the convention is reproduced here
    rather than imported; it is not a second, independent definition of
    "primary metric" (the accepted threshold-triplication precedent, D-S057-06
    Finding 2, extends the same way to this one naming convention).
    """
    task_type = metrics.task_type
    metric_name = _primary_metric_name(task_type)
    sources: dict[str, str] = {}

    pooled_model_primary = _primary_metric_value(
        metrics.pooled.get(MetricSource.MODEL.value), task_type
    )
    sources["pooled_model_primary"] = (
        f"metrics.json:pooled.{MetricSource.MODEL.value}.statistical.{metric_name}"
    )

    pooled_random_permutation_primary = _primary_metric_value(
        metrics.pooled.get(MetricSource.RANDOM_PERMUTATION.value), task_type
    )
    sources["pooled_random_permutation_primary"] = (
        f"metrics.json:pooled.{MetricSource.RANDOM_PERMUTATION.value}.statistical.{metric_name}"
    )

    fold_model_primary: dict[str, float] = {}
    fold_random_permutation_primary: dict[str, float] = {}
    for fold_id, sources_by_name in metrics.folds.items():
        model_value = _primary_metric_value(
            sources_by_name.get(MetricSource.MODEL.value), task_type
        )
        if model_value is not None:
            fold_model_primary[fold_id] = model_value
        permutation_value = _primary_metric_value(
            sources_by_name.get(MetricSource.RANDOM_PERMUTATION.value), task_type
        )
        if permutation_value is not None:
            fold_random_permutation_primary[fold_id] = permutation_value
    sources["fold_model_primary"] = (
        f"metrics.json:folds.<fold_id>.{MetricSource.MODEL.value}.statistical.{metric_name}"
    )
    sources["fold_random_permutation_primary"] = (
        f"metrics.json:folds.<fold_id>.{MetricSource.RANDOM_PERMUTATION.value}"
        f".statistical.{metric_name}"
    )

    fold_train_primary: dict[str, float] = {}
    fold_test_primary: dict[str, float] = {}
    if metrics.fold_primary is not None:
        for fold_id, values in metrics.fold_primary.items():
            train_value = values.get("train_primary")
            test_value = values.get("test_primary")
            if train_value is not None:
                fold_train_primary[fold_id] = train_value
            if test_value is not None:
                fold_test_primary[fold_id] = test_value
        sources["fold_train_primary"] = "metrics.json:fold_primary.<fold_id>.train_primary"
        sources["fold_test_primary"] = "metrics.json:fold_primary.<fold_id>.test_primary"
    else:
        sources["fold_train_primary"] = (
            "metrics.json:fold_primary (absent — optional field, D-S057-07)"
        )
        sources["fold_test_primary"] = (
            "metrics.json:fold_primary (absent — optional field, D-S057-07)"
        )

    fold_summary = dataset_manifest.fold_summary
    fold_count = len(metrics.folds)
    sources["fold_count"] = "metrics.json:folds (key count)"

    role_counts_raw = fold_summary.get("role_counts")
    role_counts = (
        {str(role): int(count) for role, count in role_counts_raw.items()}
        if isinstance(role_counts_raw, Mapping)
        else None
    )
    sources["role_counts"] = "dataset manifest.json:fold_summary.role_counts"

    fold_test_row_counts: dict[str, int] = {}
    per_fold_raw = fold_summary.get("per_fold")
    if isinstance(per_fold_raw, Sequence) and not isinstance(per_fold_raw, (str, bytes)):
        for entry in per_fold_raw:
            if not isinstance(entry, Mapping):
                continue
            entry_fold_id = entry.get("fold_id")
            test_count = entry.get(FoldRole.TEST.value)
            if entry_fold_id is not None and test_count is not None:
                fold_test_row_counts[str(entry_fold_id)] = int(test_count)
    sources["fold_test_row_counts"] = (
        f"dataset manifest.json:fold_summary.per_fold[].{FoldRole.TEST.value}"
    )

    study_spec = dataset_manifest.study_spec
    split_payload = study_spec.get("split", {})
    label_payload = study_spec.get("label", {})
    embargo_span = _optional_bar_duration_to_timedelta(
        split_payload.get("embargo_span") if isinstance(split_payload, Mapping) else None
    )
    sources["embargo_span"] = "dataset manifest.json:study_spec.split.embargo_span"
    label_horizon = _optional_bar_duration_to_timedelta(
        label_payload.get("horizon") if isinstance(label_payload, Mapping) else None
    )
    sources["label_horizon"] = "dataset manifest.json:study_spec.label.horizon"

    exclusion_counts = dict(dataset_manifest.exclusion_counts)
    sources["exclusion_counts"] = "dataset manifest.json:exclusion_counts"

    if dataset_manifest.sample_provenance is not None:
        sample_provenance: Mapping[str, Any] | None = dataset_manifest.sample_provenance.to_dict()
        sources["sample_provenance"] = "dataset manifest.json:sample_provenance"
    else:
        sample_provenance = None
        sources["sample_provenance"] = (
            "dataset manifest.json:sample_provenance (absent — predictive_dataset.v1 schema)"
        )

    minority_class_share: float | None = None
    if task_type is not TaskType.CLASSIFICATION:
        sources["minority_class_share"] = (
            "dataset features.parquet (not applicable — REGRESSION task, "
            "R3(c) is CLASSIFICATION-only)"
        )
    elif not pooled_test_labels:
        sources["minority_class_share"] = (
            "dataset features.parquet:TEST-role label column (not provided to extraction)"
        )
    else:
        labels = list(pooled_test_labels)
        positives = sum(1 for value in labels if value > 0.0)
        minority_class_share = min(positives, len(labels) - positives) / len(labels)
        sources["minority_class_share"] = "dataset features.parquet:TEST-role label column"

    feature_importance: dict[str, dict[str, float]] = {}
    feature_importance_missing: str | None = None
    if importance is None:
        feature_importance_missing = "importance.json not present (optional artifact, D-S057-05)"
        sources["feature_importance"] = "importance.json (absent — optional artifact)"
    else:
        for fold in importance.folds:
            feature_importance[str(fold.fold_id)] = dict(
                zip(
                    fold.permutation.feature_names,
                    fold.permutation.importances_mean,
                    strict=True,
                )
            )
        sources["feature_importance"] = (
            "importance.json:folds[].permutation.{feature_names,importances_mean}"
        )

    return VerdictFacts(
        task_type=task_type,
        pooled_model_primary=pooled_model_primary,
        pooled_random_permutation_primary=pooled_random_permutation_primary,
        fold_model_primary=fold_model_primary,
        fold_random_permutation_primary=fold_random_permutation_primary,
        fold_train_primary=fold_train_primary,
        fold_test_primary=fold_test_primary,
        fold_test_row_counts=fold_test_row_counts,
        fold_count=fold_count,
        role_counts=role_counts,
        embargo_span=embargo_span,
        label_horizon=label_horizon,
        minority_class_share=minority_class_share,
        exclusion_counts=exclusion_counts,
        sample_provenance=sample_provenance,
        feature_importance=feature_importance,
        feature_importance_missing=feature_importance_missing,
        sources=sources,
    )


def _primary_metric_name(task_type: TaskType) -> str:
    """Same convention as ``research/reporting/predictive/quality.py::primary_metric_name``.

    Reproduced, not imported (ADR-0032 §5 forbids importing ``research.reporting``);
    see :func:`extract_verdict_facts`'s docstring for why this is not a second
    definition of "primary metric".
    """
    if task_type is TaskType.CLASSIFICATION:
        return "roc_auc"
    return "spearman_ic"


def _primary_metric_value(source: SourceMetrics | None, task_type: TaskType) -> float | None:
    """Same convention as ``quality.py::primary_metric_value`` — see ``_primary_metric_name``."""
    if source is None:
        return None
    if task_type is TaskType.CLASSIFICATION:
        return source.statistical.roc_auc
    return source.statistical.spearman_ic


def _optional_bar_duration_to_timedelta(value: object) -> timedelta | None:
    """Parse a persisted ``Timeframe.value`` bar duration string (e.g. ``"5m"``).

    ``None`` if absent. Reuses ``Timeframe`` itself, the same value object
    ``PurgedWalkForwardSplitSpec.embargo_span`` / ``LabelSpec.horizon`` are
    declared and serialized with, rather than a second parser for the same
    grammar.
    """
    if value is None:
        return None
    return timedelta(seconds=Timeframe(str(value)).total_seconds)


def _evaluate_r2(facts: VerdictFacts, rules: VerdictRuleSet) -> RuleEvaluation:
    """R2 REJECTED_LEAKAGE_RISK (D-S057-06)."""
    source = "embargo_span, label_horizon, role_counts, pooled_model_primary"
    missing = _missing_names(
        ("embargo_span", facts.embargo_span),
        ("label_horizon", facts.label_horizon),
        ("role_counts", facts.role_counts),
        ("pooled_model_primary", facts.pooled_model_primary),
    )
    if missing:
        return _not_evaluated("R2", source, missing)

    assert facts.embargo_span is not None
    assert facts.label_horizon is not None
    assert facts.role_counts is not None
    assert facts.pooled_model_primary is not None

    embargo_shorter_than_horizon = facts.embargo_span < facts.label_horizon
    purged = facts.role_counts.get("PURGED", 0)
    embargoed = facts.role_counts.get("EMBARGOED", 0)
    guards_inactive = purged == 0 and embargoed == 0 and facts.label_horizon > timedelta(0)

    is_classification = facts.task_type is TaskType.CLASSIFICATION
    ceiling = (
        rules.classification_roc_auc_ceiling
        if is_classification
        else rules.regression_spearman_ic_ceiling
    )
    effect = facts.pooled_model_primary if is_classification else abs(facts.pooled_model_primary)
    implausible_effect = effect >= ceiling

    fired = embargo_shorter_than_horizon or guards_inactive or implausible_effect
    observed = {
        "embargo_span_seconds": facts.embargo_span.total_seconds(),
        "label_horizon_seconds": facts.label_horizon.total_seconds(),
        "purged_count": purged,
        "embargoed_count": embargoed,
        "pooled_model_effect": effect,
    }
    threshold = {
        "embargo_span_lt_label_horizon": True,
        "purged_and_embargoed_zero_with_positive_horizon": True,
        "pooled_model_effect_ge": ceiling,
    }
    return RuleEvaluation("R2", fired, observed, threshold, source)


def _evaluate_r3(facts: VerdictFacts, rules: VerdictRuleSet) -> RuleEvaluation:
    """R3 REJECTED_LOW_SAMPLE (D-S057-06)."""
    source = "fold_test_row_counts, fold_count, minority_class_share"
    is_classification = facts.task_type is TaskType.CLASSIFICATION
    required: list[tuple[str, object]] = [
        ("fold_test_row_counts", facts.fold_test_row_counts or None),
        ("fold_count", facts.fold_count),
    ]
    if is_classification:
        required.append(("minority_class_share", facts.minority_class_share))
    missing = _missing_names(*required)
    if missing:
        return _not_evaluated("R3", source, missing)

    assert facts.fold_count is not None
    min_fold_test_rows = min(facts.fold_test_row_counts.values())
    below_min_rows = min_fold_test_rows < rules.min_test_rows
    below_min_folds = facts.fold_count < rules.min_folds
    minority_share = facts.minority_class_share if is_classification else None
    below_min_minority = (
        is_classification
        and minority_share is not None
        and (minority_share < rules.min_minority_class_share)
    )

    fired = below_min_rows or below_min_folds or below_min_minority
    observed = {
        "min_fold_test_rows": min_fold_test_rows,
        "fold_count": facts.fold_count,
        "minority_class_share": minority_share,
    }
    threshold = {
        "min_test_rows": rules.min_test_rows,
        "min_folds": rules.min_folds,
        "min_minority_class_share": rules.min_minority_class_share if is_classification else None,
    }
    return RuleEvaluation("R3", fired, observed, threshold, source)


def _evaluate_r4(facts: VerdictFacts, rules: VerdictRuleSet) -> RuleEvaluation:
    """R4 REJECTED_CONCENTRATION (D-S057-06)."""
    source = (
        "fold_test_row_counts, fold_count, pooled_model_primary, "
        "pooled_random_permutation_primary, fold_model_primary, fold_random_permutation_primary"
    )
    win_stats = _fold_win_stats(facts.fold_model_primary, facts.fold_random_permutation_primary)
    missing = _missing_names(
        ("fold_test_row_counts", facts.fold_test_row_counts or None),
        ("fold_count", facts.fold_count),
        ("pooled_model_primary", facts.pooled_model_primary),
        ("pooled_random_permutation_primary", facts.pooled_random_permutation_primary),
        ("fold_model_primary/fold_random_permutation_primary", win_stats),
    )
    if missing:
        return _not_evaluated("R4", source, missing)

    assert facts.fold_count is not None
    assert facts.pooled_model_primary is not None
    assert facts.pooled_random_permutation_primary is not None
    assert win_stats is not None

    total_test_rows = sum(facts.fold_test_row_counts.values())
    max_fold_rows = max(facts.fold_test_row_counts.values())
    max_single_fold_share = max_fold_rows / total_test_rows if total_test_rows else 0.0
    concentrated_rows = max_single_fold_share > rules.max_single_fold_test_share

    baseline_delta = facts.pooled_model_primary - facts.pooled_random_permutation_primary
    wins, _ = win_stats
    single_fold_win = facts.fold_count >= rules.min_folds and baseline_delta > 0.0 and wins == 1

    fired = concentrated_rows or single_fold_win
    observed = {
        "max_single_fold_test_share": max_single_fold_share,
        "fold_count": facts.fold_count,
        "baseline_delta": baseline_delta,
        "folds_beating_random_permutation": wins,
    }
    threshold = {
        "max_single_fold_test_share": rules.max_single_fold_test_share,
        "min_folds_for_single_fold_check": rules.min_folds,
        "baseline_delta_gt": 0.0,
        "single_fold_win_count": 1,
    }
    return RuleEvaluation("R4", fired, observed, threshold, source)


def _evaluate_r1(facts: VerdictFacts, rules: VerdictRuleSet) -> RuleEvaluation:
    """R1 REJECTED_OVERFIT — relative to the run's own pooled effect size (D-S057-06)."""
    source = "fold_train_primary, fold_test_primary, pooled_model_primary"
    common_folds = sorted(set(facts.fold_train_primary) & set(facts.fold_test_primary))
    missing = _missing_names(
        ("fold_primary (train/test per-fold primary metrics)", common_folds or None),
        ("pooled_model_primary", facts.pooled_model_primary),
    )
    if missing:
        return _not_evaluated("R1", source, missing)

    assert facts.pooled_model_primary is not None
    gaps = [
        facts.fold_train_primary[fold_id] - facts.fold_test_primary[fold_id]
        for fold_id in common_folds
    ]
    unanimous_overfit = all(gap > 0.0 for gap in gaps)
    median_gap = _median(gaps)
    neutral = (
        _CLASSIFICATION_NEUTRAL
        if facts.task_type is TaskType.CLASSIFICATION
        else _REGRESSION_NEUTRAL
    )
    effect_size_pooled = abs(facts.pooled_model_primary - neutral)
    gap_exceeds_effect_size = median_gap > rules.overfit_gap_ratio * effect_size_pooled

    fired = unanimous_overfit and gap_exceeds_effect_size
    observed = {
        "unanimous_train_gt_test": unanimous_overfit,
        "median_train_test_gap": median_gap,
        "effect_size_pooled": effect_size_pooled,
        "fold_count_compared": len(common_folds),
    }
    threshold = {"overfit_gap_ratio": rules.overfit_gap_ratio}
    return RuleEvaluation("R1", fired, observed, threshold, source)


def _evaluate_outcome_rules(
    facts: VerdictFacts, rules: VerdictRuleSet
) -> tuple[RuleEvaluation, RuleEvaluation, RuleEvaluation, RuleEvaluation, RuleEvaluation | None]:
    """O1..O4 (D-S057-06). Mutually exclusive and exhaustive once baseline facts exist."""
    source = (
        "pooled_model_primary, pooled_random_permutation_primary, "
        "fold_model_primary, fold_random_permutation_primary"
    )
    win_stats = _fold_win_stats(facts.fold_model_primary, facts.fold_random_permutation_primary)
    missing = _missing_names(
        ("pooled_model_primary", facts.pooled_model_primary),
        ("pooled_random_permutation_primary", facts.pooled_random_permutation_primary),
        ("fold_model_primary/fold_random_permutation_primary", win_stats),
    )
    if missing:
        o1 = _not_evaluated("O1", source, missing)
        o2 = _not_evaluated("O2", source, missing)
        o3 = _not_evaluated("O3", source, missing)
        o4 = _not_evaluated("O4", source, missing)
        return o1, o2, o3, o4, o1

    assert facts.pooled_model_primary is not None
    assert facts.pooled_random_permutation_primary is not None
    assert win_stats is not None

    baseline_delta = facts.pooled_model_primary - facts.pooled_random_permutation_primary
    wins, total = win_stats
    fold_win_rate = wins / total

    observed = {"baseline_delta": baseline_delta, "fold_win_rate": fold_win_rate}
    beats_pooled = baseline_delta > 0.0
    every_fold_wins = fold_win_rate == 1.0
    at_least_two_thirds = fold_win_rate >= rules.min_fold_win_rate

    o1_fired = beats_pooled and every_fold_wins
    o2_fired = beats_pooled and at_least_two_thirds and not every_fold_wins
    o3_fired = beats_pooled and not at_least_two_thirds
    o4_fired = not beats_pooled

    o1 = RuleEvaluation(
        "O1", o1_fired, observed, {"baseline_delta_gt": 0.0, "fold_win_rate_eq": 1.0}, source
    )
    o2 = RuleEvaluation(
        "O2",
        o2_fired,
        observed,
        {
            "baseline_delta_gt": 0.0,
            "fold_win_rate_ge": rules.min_fold_win_rate,
            "fold_win_rate_lt": 1.0,
        },
        source,
    )
    o3 = RuleEvaluation(
        "O3",
        o3_fired,
        observed,
        {"baseline_delta_gt": 0.0, "fold_win_rate_lt": rules.min_fold_win_rate},
        source,
    )
    o4 = RuleEvaluation("O4", o4_fired, observed, {"baseline_delta_le": 0.0}, source)
    return o1, o2, o3, o4, None


def _fold_win_stats(
    model: Mapping[str, float], random_permutation: Mapping[str, float]
) -> tuple[int, int] | None:
    """Return ``(wins, folds_with_both)`` or ``None`` if no fold has both sources."""
    common = sorted(set(model) & set(random_permutation))
    if not common:
        return None
    wins = sum(1 for fold_id in common if model[fold_id] > random_permutation[fold_id])
    return wins, len(common)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    midpoint = count // 2
    if count % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def _missing_names(*candidates: tuple[str, object]) -> tuple[str, ...]:
    return tuple(name for name, value in candidates if value is None)


def _not_evaluated(rule_id: str, source: str, missing: tuple[str, ...]) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        fired=False,
        observed={},
        threshold={},
        source=source,
        evaluated=False,
        missing_input=", ".join(missing),
    )
