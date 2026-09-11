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
from datetime import datetime
from typing import Any

from dashboard_app.publication.errors import UnsafePublicIdentityError
from dashboard_app.publication.identity import is_safe_identity_value, is_safe_public_text

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

_RESEARCH_CATALOG_ENTRY_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "workflow",
        "run_id",
        "title",
        "created_at_utc",
        "source_dataset_ref",
        "evaluation_timeframe",
        "framework_version",
        "artifact_schema_version",
        "research_scope",
        "experiment_id",
        "time_range_start_utc",
        "time_range_end_utc",
        "verdict",
    }
)
_RESEARCH_CATALOG_IDENTITY_FIELDS = frozenset(
    {
        "workflow",
        "run_id",
        "source_dataset_ref",
        "evaluation_timeframe",
        "framework_version",
        "artifact_schema_version",
        "research_scope",
        "experiment_id",
    }
)
_RESEARCH_CATALOG_TEXT_FIELDS = frozenset({"title", "verdict"})
_RESEARCH_CATALOG_TIMESTAMP_FIELDS = frozenset(
    {"created_at_utc", "time_range_start_utc", "time_range_end_utc"}
)
_RESEARCH_CATALOG_REQUIRED_FIELDS = frozenset({"workflow", "run_id", "title"})
_RESEARCH_CATALOG_WORKFLOWS = frozenset(
    {"market", "signal", "strategy", "robustness", "predictive"}
)

_SIGNAL_EVIDENCE_ALLOWED_FIELDS = frozenset(
    {
        "run_id",
        "schema_version",
        "framework_version",
        "created_at_utc",
        "source_dataset_ref",
        "evaluation_timeframe",
        "signal_model_ids",
        "market_model_ids",
        "horizon_bars_requested",
        "experiment_id",
        "research_scope",
        "research_question",
    }
)
_SIGNAL_EVIDENCE_TABLE_COLUMNS: Mapping[str, frozenset[str]] = {
    "summary_metrics": frozenset(
        {
            "run_id",
            "research_scope",
            "horizon_bars",
            "sample_size_total",
            "sample_size_complete",
            "sample_size_incomplete",
            "completion_rate",
            "minimum_required",
            "metrics_eligible",
            "forward_return_mean",
            "forward_return_median",
            "hit_rate",
            "mfe_mean",
            "mfe_median",
            "mae_mean",
            "mae_median",
        }
    ),
    "grouped_summaries": frozenset(
        {
            "run_id",
            "research_scope",
            "horizon_bars",
            "group_dimension",
            "group_value",
            "sample_size_total",
            "sample_size_complete",
            "sample_size_incomplete",
            "metrics_eligible",
            "forward_return_mean",
            "forward_return_median",
            "hit_rate",
            "mfe_mean",
            "mfe_median",
            "mae_mean",
            "mae_median",
        }
    ),
    "distribution_summaries": frozenset(
        {
            "run_id",
            "horizon_bars",
            "sample_size_complete",
            "minimum_required",
            "interpretation_minimum_required",
            "metrics_computable",
            "metrics_interpretable",
            "forward_return_p10",
            "forward_return_p25",
            "forward_return_p75",
            "forward_return_p90",
            "forward_return_std",
            "forward_return_min",
            "forward_return_max",
        }
    ),
    "conditional_comparison": frozenset(
        {
            "run_id",
            "horizon_bars",
            "context_true_sample_size",
            "context_false_sample_size",
            "context_missing_sample_size",
            "comparison_status",
            "status_reason",
            "forward_return_mean_true",
            "forward_return_mean_false",
            "forward_return_mean_delta",
            "forward_return_median_true",
            "forward_return_median_false",
            "forward_return_median_delta",
            "hit_rate_true",
            "hit_rate_false",
            "hit_rate_delta",
            "mfe_mean_true",
            "mfe_mean_false",
            "mfe_mean_delta",
            "mfe_median_true",
            "mfe_median_false",
            "mfe_median_delta",
            "mae_mean_true",
            "mae_mean_false",
            "mae_mean_delta",
            "mae_median_true",
            "mae_median_false",
            "mae_median_delta",
        }
    ),
    "join_diagnostics": frozenset(
        {
            "run_id",
            "horizon_bars",
            "entity_count",
            "outcome_rows_total",
            "outcome_rows_complete",
            "outcome_rows_unmatched_entity",
            "matched_context_rows",
            "missing_context_rows",
            "duplicate_context_matches",
            "context_true_complete",
            "context_false_complete",
            "context_missing_complete",
            "overlapping_outcome_windows",
            "overlapping_outcome_rate",
        }
    ),
    "metric_histograms": frozenset(
        {
            "run_id",
            "horizon_bars",
            "metric",
            "bin_index",
            "bin_start",
            "bin_end",
            "count",
            "reference_mean",
            "reference_median",
        }
    ),
    "quality_warnings": frozenset({"code", "message", "horizon_bars"}),
}

_ROBUSTNESS_EVIDENCE_ALLOWED_FIELDS = frozenset(
    {
        "experiment_id",
        "schema_version",
        "framework_version",
        "created_at_utc",
        "source_dataset_ref",
        "evaluation_timeframe",
        "requested_range_start",
        "requested_range_end",
        "strategy_template_id",
        "evidence_label",
    }
)
_ROBUSTNESS_EVIDENCE_TABLE_COLUMNS: Mapping[str, frozenset[str]] = {
    "parameter_sweep_rankings": frozenset(
        {
            "experiment_id",
            "ranking_metric",
            "rank",
            "config_id",
            "strategy_run_id",
            "metric",
            "metric_value",
            "net_pnl",
            "max_drawdown",
            "win_rate",
            "trade_count",
        }
    ),
    "parameter_sweep_heatmap": frozenset(
        {"experiment_id", "metric", "x_axis", "y_axis", "x_value", "y_value", "value"}
    ),
    "walk_forward_folds": frozenset(
        {
            "experiment_id",
            "fold_id",
            "fold_index",
            "config_id",
            "train_net_pnl",
            "oos_strategy_run_id",
            "oos_trade_count",
            "oos_net_pnl",
            "oos_max_drawdown",
            "oos_final_equity",
        }
    ),
    "walk_forward_equity": frozenset({"experiment_id", "observed_at", "equity", "drawdown"}),
    "stress_comparison": frozenset(
        {
            "experiment_id",
            "baseline_strategy_run_id",
            "baseline_net_pnl",
            "baseline_trade_count",
            "scenario_id",
            "mode",
            "status",
            "net_pnl",
            "trade_count",
            "delta_net_pnl",
            "strategy_run_id",
        }
    ),
    "monte_carlo_distributions": frozenset(
        {
            "experiment_id",
            "method",
            "path_count",
            "mean_terminal_equity",
            "p5_terminal_equity",
            "p50_terminal_equity",
            "p95_terminal_equity",
        }
    ),
    "monte_carlo_tails": frozenset(
        {
            "experiment_id",
            "method",
            "probability_terminal_pnl_negative",
            "probability_max_drawdown_exceeds_threshold",
        }
    ),
}
_ROBUSTNESS_VERDICT_ALLOWED_FIELDS = frozenset(
    {"verdict", "summary", "strengths", "weaknesses", "blocking_issues"}
)
_ROBUSTNESS_GATE_ALLOWED_FIELDS = frozenset(
    {"gate_id", "passed", "severity", "message", "observed_value"}
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


def sanitize_research_catalog_entry(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copy the reviewed public identity fields for one research catalog row."""
    sanitized = {
        key: raw[key]
        for key in _RESEARCH_CATALOG_ENTRY_ALLOWED_FIELDS
        if key in raw and raw[key] is not None
    }
    missing = _RESEARCH_CATALOG_REQUIRED_FIELDS.difference(sanitized)
    if missing:
        raise UnsafePublicIdentityError(
            f"missing required public catalog fields: {', '.join(sorted(missing))}"
        )
    if sanitized["workflow"] not in _RESEARCH_CATALOG_WORKFLOWS:
        raise UnsafePublicIdentityError(
            f"unsupported public catalog workflow: {sanitized['workflow']!r}"
        )
    for key in _RESEARCH_CATALOG_IDENTITY_FIELDS:
        value = sanitized.get(key)
        if value is not None and (not isinstance(value, str) or not is_safe_identity_value(value)):
            raise UnsafePublicIdentityError(f"unsafe public {key}: {value!r}")
    for key in _RESEARCH_CATALOG_TEXT_FIELDS:
        value = sanitized.get(key)
        if value is not None and (not isinstance(value, str) or not is_safe_public_text(value)):
            raise UnsafePublicIdentityError(f"unsafe public {key}: {value!r}")
    for key in _RESEARCH_CATALOG_TIMESTAMP_FIELDS:
        value = sanitized.get(key)
        if value is not None and not _is_aware_iso_timestamp(value):
            raise UnsafePublicIdentityError(f"unsafe public {key}: {value!r}")
    return sanitized


def sanitize_signal_research_evidence(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Project rich Signal Research facts through explicit field/table allowlists."""
    sanitized = {
        key: raw[key]
        for key in _SIGNAL_EVIDENCE_ALLOWED_FIELDS
        if key in raw and raw[key] is not None
    }
    _require_safe_evidence_identity(sanitized, "run_id")
    tables = _sanitize_evidence_tables(raw.get("tables"), _SIGNAL_EVIDENCE_TABLE_COLUMNS)
    if "summary_metrics" not in tables:
        raise UnsafePublicIdentityError("signal research evidence requires summary_metrics")
    sanitized["tables"] = tables
    _validate_public_tree(sanitized)
    return sanitized


def sanitize_robustness_research_evidence(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Project the approved legacy robustness demo without its private config."""
    sanitized = {
        key: raw[key]
        for key in _ROBUSTNESS_EVIDENCE_ALLOWED_FIELDS
        if key in raw and raw[key] is not None
    }
    _require_safe_evidence_identity(sanitized, "experiment_id")
    if sanitized["experiment_id"] != "demo-robustness-nq-half-year":
        raise UnsafePublicIdentityError("unsupported public robustness evidence")

    raw_verdict = raw.get("verdict")
    if isinstance(raw_verdict, Mapping):
        verdict = {
            key: raw_verdict[key]
            for key in _ROBUSTNESS_VERDICT_ALLOWED_FIELDS
            if key in raw_verdict
        }
        raw_gates = raw_verdict.get("gate_results")
        if isinstance(raw_gates, list):
            verdict["gate_results"] = [
                {key: gate[key] for key in _ROBUSTNESS_GATE_ALLOWED_FIELDS if key in gate}
                for gate in raw_gates
                if isinstance(gate, Mapping)
            ]
        sanitized["verdict"] = verdict

    tables = _sanitize_evidence_tables(raw.get("tables"), _ROBUSTNESS_EVIDENCE_TABLE_COLUMNS)
    if "walk_forward_folds" not in tables:
        raise UnsafePublicIdentityError("robustness evidence requires walk_forward_folds")
    sanitized["tables"] = tables
    _validate_public_tree(sanitized)
    return sanitized


def _sanitize_evidence_tables(
    raw_tables: Any,
    allowed_tables: Mapping[str, frozenset[str]],
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(raw_tables, Mapping):
        return {}
    sanitized: dict[str, list[dict[str, Any]]] = {}
    for table_name, allowed_columns in allowed_tables.items():
        raw_rows = raw_tables.get(table_name)
        if not isinstance(raw_rows, list):
            continue
        sanitized[table_name] = [
            {key: row[key] for key in allowed_columns if key in row}
            for row in raw_rows
            if isinstance(row, Mapping)
        ]
    return sanitized


def _require_safe_evidence_identity(payload: Mapping[str, Any], key: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not is_safe_identity_value(value):
        raise UnsafePublicIdentityError(f"unsafe public {key}: {value!r}")


def _validate_public_tree(value: Any) -> None:
    """Reject path-like or non-JSON values even when their field is allowlisted."""
    if value is None or isinstance(value, bool | int | float):
        return
    if isinstance(value, str):
        if value and not is_safe_public_text(value):
            raise UnsafePublicIdentityError(f"unsafe path-like public evidence value: {value!r}")
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _validate_public_tree(item)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _validate_public_tree(item)
        return
    raise UnsafePublicIdentityError(
        f"unsupported public evidence value type: {type(value).__name__}"
    )


def _is_aware_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() is not None


#: Registry: artifact_role name -> sanitizer function, used by generator.py.
#: This is the seam Sprint 060 extends -- adding a role means adding one new
#: function and one new entry here, never editing an existing pair.
_SANITIZERS: Mapping[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "predictive_run_verdict": sanitize_verdict_report,
    "promoted_artifact_identity": sanitize_promoted_artifact_identity,
    "predictive_run_metrics": sanitize_predictive_run_metrics,
    "predictive_threshold_sensitivity": sanitize_predictive_threshold_sensitivity,
    "strategy_research_run_summary": sanitize_strategy_research_run_summary,
    "research_catalog_entry": sanitize_research_catalog_entry,
    "signal_research_evidence": sanitize_signal_research_evidence,
    "robustness_research_evidence": sanitize_robustness_research_evidence,
}


def sanitizer_for_role(artifact_role: str) -> Callable[[Mapping[str, Any]], dict[str, Any]] | None:
    """Return the sanitizer registered for ``artifact_role``, or ``None`` if unknown."""
    return _SANITIZERS.get(artifact_role)
