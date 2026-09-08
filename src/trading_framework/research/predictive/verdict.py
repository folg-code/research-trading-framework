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

Fact *extraction* (turning a persisted ``metrics.json`` / dataset manifest /
``importance.json`` into a :class:`VerdictFacts`) is out of scope here
(S057-T003). File I/O and sidecar persistence are out of scope here too
(S057-T004). This module only declares the vocabulary and computes a verdict
from an already-built :class:`VerdictFacts`.

Rule order is fixed and part of the contract: ``R2, R3, R4, R1``, then
``O1..O4`` (D-S057-06). The first rejection rule that fires determines the
verdict; every one of the eight rules is still evaluated and recorded in the
returned :class:`VerdictReport`. A rule whose required fact is missing from
``VerdictFacts`` is recorded as not evaluated (never as not-fired, never
silently skipped), and the overall verdict is ``INCONCLUSIVE`` naming the
missing input, unless an earlier rejection rule already fired.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import TaskType

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

    This dataclass is built by hand in this package's own tests; turning a
    real ``PredictiveMetricsReport`` / dataset manifest / ``importance.json``
    into one is S057-T003's job, not this module's.
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
