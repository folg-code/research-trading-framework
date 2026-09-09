"""Deny-by-default field allowlists, one per artifact role (ADR-0034 S1.3).

Every sanitizer here is a plain ``dict``-in/``dict``-out function over an
explicit ``frozenset[str]`` allowlist -- no wildcard, no ``**raw``, no
"copy everything except a blocklist" anywhere. A forbidden or newly
appearing upstream field can never reach a projected artifact because it was
never named, not because something else stripped it. This mirrors
``dashboard_app.catalog.scanner``'s ``_identity_fields`` allowlist pattern,
but is typed to a role, versioned via the artifact it feeds, and tested for
both retention and omission.

Only two representative artifact roles are implemented in Sprint 059 T002 --
the richest realistic nested shape (a persisted predictive-run verdict
report) and the degenerate scalar-only shape (a promoted artifact's bare
fingerprint identity). The full Sprint 060 field inventory (dataset
summaries, threshold-sensitivity rows, Strategy Research run summaries) is
explicitly out of scope here; adding a role means adding one new function
and one new ``_SANITIZERS`` entry, never touching the existing ones
(ADR-0034 S5, additive).
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


#: Registry: artifact_role name -> sanitizer function, used by generator.py.
#: This is the seam Sprint 060 extends -- adding a role means adding one new
#: function and one new entry here, never editing an existing pair.
_SANITIZERS: Mapping[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "predictive_run_verdict": sanitize_verdict_report,
    "promoted_artifact_identity": sanitize_promoted_artifact_identity,
}


def sanitizer_for_role(artifact_role: str) -> Callable[[Mapping[str, Any]], dict[str, Any]] | None:
    """Return the sanitizer registered for ``artifact_role``, or ``None`` if unknown."""
    return _SANITIZERS.get(artifact_role)
