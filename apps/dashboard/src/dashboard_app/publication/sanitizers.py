"""Deny-by-default field allowlists, one per artifact role (ADR-0034 S1.3).

Every sanitizer here is a plain ``dict``-in/``dict``-out function over an
explicit ``frozenset[str]`` allowlist -- no wildcard, no ``**raw``, no
"copy everything except a blocklist" anywhere. A forbidden or newly
appearing upstream field can never reach a projected artifact because it was
never named, not because something else stripped it. This mirrors
``dashboard_app.catalog.scanner``'s ``_identity_fields`` allowlist pattern,
but is typed to a role, versioned via the artifact it feeds, and tested for
both retention and omission.

Sprint 059 T002 shipped two representative roles (a persisted predictive-run
verdict report; a promoted artifact's bare fingerprint identity). Sprint 060
T003 adds the three roles T001's field inventory
(``SPRINT_060_T001_FIELD_INVENTORY.md``) froze for the BTC Signal Quality
study's charts: pooled/per-fold ROC AUC, threshold-sensitivity coverage and
hit-rate, and a Strategy Research run's trade disposition summary. Adding a
role means adding one new function and one new ``_SANITIZERS`` entry, never
touching the existing ones (ADR-0034 S5, additive).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

#: Top-level fields of a persisted ``verdict.json`` payload
#: (`trading_framework.application.predictive_research.evaluate_run_verdict`)
#: that are safe to copy verbatim. ``rule_set``, ``facts``, ``run_id``,
#: ``dataset_id`` and ``dataset_fingerprint`` are deliberately withheld here
#: pending Sprint 060 T001's field freeze -- this role proves the mechanism,
#: not the complete public shape of a verdict.
_VERDICT_REPORT_ALLOWED_FIELDS: frozenset[str] = frozenset({"verdict", "rule_set_version"})

#: Per-entry fields of the persisted ``rules`` list
#: (``trading_framework.research.predictive.verdict.RuleEvaluation.to_dict()``).
_RULE_EVALUATION_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"rule_id", "fired", "observed", "threshold", "source", "evaluated", "missing_input"}
)

#: The only field of a persisted promoted-artifact ``manifest.json``
#: (``trading_framework.research.datasets.promoted_artifact.PromotedArtifactManifest``)
#: exposed publicly -- ADR-0034 S2.5: "as a bare identity string". Every
#: other manifest field (``preprocessing_spec``, ``estimator_spec``,
#: ``training_library`` etc.) looks like config/IP, not a persisted public
#: fact, and stays private.
_PROMOTED_ARTIFACT_IDENTITY_ALLOWED_FIELDS: frozenset[str] = frozenset({"artifact_fingerprint"})


def sanitize_verdict_report(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy-never-derive allowlist for a persisted ``verdict.json`` payload.

    The raw payload's rule evaluations are persisted under the key
    ``"rules"`` (see ``evaluate_run_verdict._verdict_sidecar_payload``); the
    sanitized output renames this to ``"evaluations"`` to match this
    package's own naming (``VerdictReport.evaluations``) -- a presentation
    naming choice, not a change to what is exposed.
    """
    sanitized = {key: raw[key] for key in _VERDICT_REPORT_ALLOWED_FIELDS if key in raw}
    raw_rules = raw.get("rules")
    if isinstance(raw_rules, list):
        sanitized["evaluations"] = [
            {key: entry[key] for key in _RULE_EVALUATION_ALLOWED_FIELDS if key in entry}
            for entry in raw_rules
            if isinstance(entry, Mapping)
        ]
    return sanitized


def sanitize_promoted_artifact_identity(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy-never-derive allowlist for a persisted promoted-artifact manifest."""
    return {key: raw[key] for key in _PROMOTED_ARTIFACT_IDENTITY_ALLOWED_FIELDS if key in raw}


#: Top-level fields of a persisted ``metrics.json`` payload
#: (``trading_framework.research.predictive.metrics``) that are safe to copy
#: verbatim -- SPRINT_060_T001_FIELD_INVENTORY.md Chart 1 / Q2.
_PREDICTIVE_RUN_METRICS_ALLOWED_FIELDS: frozenset[str] = frozenset({"decision_threshold", "seed"})

#: The only field kept from a ``pooled.<SOURCE>.statistical`` or
#: ``folds.<fold_id>.<SOURCE>.statistical`` mapping.
_METRIC_SOURCE_STATISTICAL_ALLOWED_FIELDS: frozenset[str] = frozenset({"roc_auc"})

#: The two comparators charted against each other (Chart 1) -- MAJORITY_CLASS
#: is a real ``pooled`` key too but no accepted chart reads it, so it stays
#: private rather than allowlisted speculatively.
_METRIC_SOURCES: tuple[str, ...] = ("MODEL", "RANDOM_PERMUTATION")

#: Per-point fields of a persisted ``threshold_sensitivity.json`` payload
#: (``trading_framework.research.predictive.threshold_sensitivity``) --
#: SPRINT_060_T001_FIELD_INVENTORY.md Chart 2.
_THRESHOLD_SENSITIVITY_POINT_ALLOWED_FIELDS: frozenset[str] = frozenset({"threshold"})
_THRESHOLD_SENSITIVITY_FINANCE_ALLOWED_FIELDS: frozenset[str] = frozenset({"coverage", "hit_rate"})

#: Fields of a persisted Strategy Research ``summary_metrics.parquet`` row
#: (one row per run) that are safe to copy verbatim --
#: SPRINT_060_T001_FIELD_INVENTORY.md Q3 / Chart 3. ``win_count``,
#: ``loss_count`` and ``mean_net_pnl`` are not real columns of this artifact
#: (T001 confirmed) and so cannot be allowlisted here -- they do not exist
#: to copy.
_STRATEGY_RUN_SUMMARY_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"run_id", "trade_count", "win_rate", "net_pnl"}
)


def _sanitize_metric_source_mapping(raw_source_group: Any) -> dict[str, Any]:
    """Allowlist one ``{"MODEL": {...}, "RANDOM_PERMUTATION": {...}, ...}`` mapping.

    Shared by the ``pooled`` and each ``folds.<fold_id>`` entry -- both have
    the identical shape in ``metrics.json``.
    """
    sanitized: dict[str, Any] = {}
    if not isinstance(raw_source_group, Mapping):
        return sanitized
    for source in _METRIC_SOURCES:
        source_payload = raw_source_group.get(source, {})
        if not isinstance(source_payload, Mapping):
            continue
        values = source_payload.get("statistical", {})
        if not isinstance(values, Mapping):
            continue
        kept = {
            key: values[key] for key in _METRIC_SOURCE_STATISTICAL_ALLOWED_FIELDS if key in values
        }
        if kept:
            sanitized[source] = {"statistical": kept}
    return sanitized


def sanitize_predictive_run_metrics(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy-never-derive allowlist for a persisted ``metrics.json`` payload.

    Keeps only the pooled and per-fold ``MODEL``/``RANDOM_PERMUTATION``
    pooled ROC AUC values Chart 1 needs, plus the two run-level assumption
    fields (``decision_threshold``, ``seed``) Q2 needs -- never ``run_id``,
    ``dataset_id`` or ``dataset_fingerprint`` (T001 deliberately withheld
    those, matching ``sanitize_verdict_report``).
    """
    sanitized = {key: raw[key] for key in _PREDICTIVE_RUN_METRICS_ALLOWED_FIELDS if key in raw}

    pooled = _sanitize_metric_source_mapping(raw.get("pooled"))
    if pooled:
        sanitized["pooled"] = pooled

    raw_folds = raw.get("folds")
    if isinstance(raw_folds, Mapping):
        folds: dict[str, Any] = {}
        for fold_id, fold_payload in raw_folds.items():
            sanitized_fold = _sanitize_metric_source_mapping(fold_payload)
            if sanitized_fold:
                folds[str(fold_id)] = sanitized_fold
        if folds:
            sanitized["folds"] = folds

    return sanitized


def sanitize_predictive_threshold_sensitivity(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy-never-derive allowlist for a persisted ``threshold_sensitivity.json`` payload."""
    raw_points = raw.get("points")
    if not isinstance(raw_points, list):
        return {}

    points: list[dict[str, Any]] = []
    for entry in raw_points:
        if not isinstance(entry, Mapping):
            continue
        sanitized_point = {
            key: entry[key] for key in _THRESHOLD_SENSITIVITY_POINT_ALLOWED_FIELDS if key in entry
        }
        finance = entry.get("finance")
        if isinstance(finance, Mapping):
            sanitized_finance = {
                key: finance[key]
                for key in _THRESHOLD_SENSITIVITY_FINANCE_ALLOWED_FIELDS
                if key in finance
            }
            if sanitized_finance:
                sanitized_point["finance"] = sanitized_finance
        if sanitized_point:
            points.append(sanitized_point)

    return {"points": points} if points else {}


def sanitize_strategy_research_run_summary(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy-never-derive allowlist for one persisted ``summary_metrics.parquet`` row."""
    return {key: raw[key] for key in _STRATEGY_RUN_SUMMARY_ALLOWED_FIELDS if key in raw}


#: Registry: artifact_role name -> sanitizer function, used by generator.py.
#: This is the seam Sprint 060 extends -- adding a role means adding one new
#: function and one new entry here, never editing an existing pair.
_SANITIZERS: Mapping[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "predictive_run_verdict": sanitize_verdict_report,
    "promoted_artifact_identity": sanitize_promoted_artifact_identity,
    "predictive_run_metrics": sanitize_predictive_run_metrics,
    "predictive_threshold_sensitivity": sanitize_predictive_threshold_sensitivity,
    "strategy_research_run_summary": sanitize_strategy_research_run_summary,
}


def sanitizer_for_role(artifact_role: str) -> Callable[[Mapping[str, Any]], dict[str, Any]] | None:
    """Return the sanitizer registered for ``artifact_role``, or ``None`` if unknown."""
    return _SANITIZERS.get(artifact_role)
